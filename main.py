import os
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from database import db, create_document, get_documents
from schemas import Event, Reservation, Ownerprofile, Theater, Contactmessage, Video

app = FastAPI(title="Vienna Cabaret Theater API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Cabaret Theater API running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name
            response["connection_status"] = "Connected"
            try:
                response["collections"] = db.list_collection_names()
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response


# Utilities

def collection_name(model_cls) -> str:
    return model_cls.__name__.lower()


# Events
@app.get("/api/events", response_model=List[Event])
def list_events():
    docs = db[collection_name(Event)].find({}).sort("date", 1)
    return [
        Event(**{**d, "id": str(d.get("_id"))}) for d in docs
    ]


# Reservations
class ReservationResponse(BaseModel):
    reservation_id: str
    message: str


@app.post("/api/reservations", response_model=ReservationResponse)
def create_reservation(res: Reservation):
    # Check event exists and seats available, then atomically decrement
    ev = db[collection_name(Event)].find_one({"_id": {"$eq": res.event_id}})
    # res.event_id is str; mongo _id is ObjectId normally. For simplicity, also allow string IDs from seed.
    # Try both string and ObjectId
    from bson import ObjectId
    event = None
    try:
        event = db[collection_name(Event)].find_one({"_id": ObjectId(res.event_id)})
    except Exception:
        event = db[collection_name(Event)].find_one({"_id": res.event_id})

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if int(event.get("seats_available", 0)) < res.tickets:
        raise HTTPException(status_code=400, detail="Not enough seats available")

    # Decrement seats in a single operation with condition
    from pymongo import ReturnDocument
    updated = db[collection_name(Event)].find_one_and_update(
        {"_id": event["_id"], "seats_available": {"$gte": res.tickets}},
        {"$inc": {"seats_available": -res.tickets}, "$set": {"updated_at": datetime.utcnow()}},
        return_document=ReturnDocument.AFTER
    )
    if not updated:
        raise HTTPException(status_code=409, detail="Seats no longer available")

    reservation_id = create_document(collection_name(Reservation), res.model_dump())
    return {"reservation_id": reservation_id, "message": "Reservation confirmed"}


# Owners
@app.get("/api/owners", response_model=List[Ownerprofile])
def list_owners():
    docs = get_documents(collection_name(Ownerprofile))
    return [Ownerprofile(**{k: v for k, v in d.items() if k != "_id"}) for d in docs]


# Theater info (latest document)
@app.get("/api/theater", response_model=Optional[Theater])
def theater_info():
    doc = db[collection_name(Theater)].find_one(sort=[("created_at", -1)])
    if not doc:
        return None
    return Theater(**{k: v for k, v in doc.items() if k != "_id"})


# Contact message
class ContactResponse(BaseModel):
    message_id: str
    message: str


@app.post("/api/contact", response_model=ContactResponse)
def send_message(msg: Contactmessage):
    mid = create_document(collection_name(Contactmessage), msg)
    return {"message_id": mid, "message": "Thanks for reaching out!"}


# Video background
@app.get("/api/video/current", response_model=Optional[Video])
def current_video():
    key = datetime.utcnow().strftime("%Y-%m")
    doc = db[collection_name(Video)].find_one({"month_key": key})
    if not doc:
        # Fallback: the most recent video
        doc = db[collection_name(Video)].find_one(sort=[("created_at", -1)])
    if not doc:
        return None
    return Video(**{k: v for k, v in doc.items() if k != "_id"})


@app.get("/api/video/{month_key}", response_model=Optional[Video])
def video_by_month(month_key: str):
    doc = db[collection_name(Video)].find_one({"month_key": month_key})
    if not doc:
        return None
    return Video(**{k: v for k, v in doc.items() if k != "_id"})


# Optional: seed endpoint to populate demo content
@app.post("/api/seed")
def seed():
    """Populate the database with sample data for preview."""
    # Only seed if empty
    if db[collection_name(Event)].estimated_document_count() > 0:
        return {"status": "ok", "message": "Already seeded"}

    # Theater
    create_document(
        collection_name(Theater),
        Theater(
            name="Kabarett Salon am Kanal",
            tagline="Quirky. Wien. Mit Schmäh.",
            story=(
                "Geboren aus dem Geist der Kaffeehauskultur, lebt unser kleines Kabarett die große Liebe "
                "zum spontanen Wort. Zwischen Samtvorhängen und Messinglampen trifft moderner Humor auf "
                "den Charme vergangener Nächte."
            ),
            address="Schwarzer-Bären-Gasse 12, 1050 Wien",
            phone="+43 1 234 56 78",
            email="kontakt@kabarett-salon.at",
            opening_hours="Di–So ab 18:00",
            transport_howto="U4 bis Kettenbrückengasse, dann 5 Minuten zu Fuß"
        )
    )

    # Owners
    owners = [
        Ownerprofile(
            name="Lena Weiss",
            role="Leitung & Bühne",
            bio="Kabarettistin, Dramaturgin und Barflüsterin. Liebt Altbaufliesen und schnelle Pointen.",
            image_url="https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=600&h=600&fit=crop",
            instagram="https://instagram.com/lenakabarett",
            website=None,
        ),
        Ownerprofile(
            name="Milo Berger",
            role="Impro & Programm",
            bio="Impro-Spieler und Organisator. Findet Geschichten in jeder U-Bahnfahrt.",
            image_url="https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=600&h=600&fit=crop",
            instagram=None,
            website="https://miloberger.example.com",
        ),
    ]
    for o in owners:
        create_document(collection_name(Ownerprofile), o)

    # Events (next days)
    base_date = datetime.utcnow()
    demo_events = [
        Event(
            title="Wiener Schmäh & Schnapsidee",
            description="Kabarett-Abend mit Biss und Bussi.",
            genre="Kabarett",
            date=base_date.replace(hour=19, minute=30, second=0, microsecond=0),
            duration_minutes=90,
            price_eur=18.0,
            seats_total=60,
            seats_available=60,
            image_url="https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=1200&auto=format&fit=crop&q=60"
        ),
        Event(
            title="Impro am Kanal: Alles kann passieren",
            description="Improvisationstheater – du gibst vor, wir legen los!",
            genre="Impro",
            date=(base_date.replace(hour=20, minute=0, second=0, microsecond=0)),
            duration_minutes=75,
            price_eur=15.0,
            seats_total=60,
            seats_available=60,
            image_url="https://images.unsplash.com/photo-1515165562835-c3b8c1ea0f59?w=1200&auto=format&fit=crop&q=60"
        ),
        Event(
            title="Werkstatt Humor: Basics für Einsteiger:innen",
            description="Workshop für spontane Bühnenmenschen.",
            genre="Workshop",
            date=(base_date.replace(day=min(base_date.day + 3, 28), hour=18, minute=0, second=0, microsecond=0)),
            duration_minutes=120,
            price_eur=40.0,
            seats_total=20,
            seats_available=20,
            image_url="https://images.unsplash.com/photo-1496307042754-b4aa456c4a2d?w=1200&auto=format&fit=crop&q=60"
        ),
    ]
    for e in demo_events:
        create_document(collection_name(Event), e)

    # Video for current month
    create_document(
        collection_name(Video),
        Video(
            month_key=datetime.utcnow().strftime("%Y-%m"),
            video_url="https://cdn.coverr.co/videos/coverr-theatre-actors-having-fun-0044/1080p.mp4",
            caption="Aus dem aktuellen Programm"
        )
    )

    return {"status": "ok", "message": "Seeded demo data"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

import logging
import os
import traceback
from io import BytesIO
from typing import List, Optional

from db import Contact, ContactFile, ContactProject, ContactTag, get_db
from fastapi import APIRouter, HTTPException, UploadFile
from PIL import Image
from pydantic import BaseModel
from sqlalchemy import or_
from starlette.responses import FileResponse

router = APIRouter(tags=["Contacts"])

AVATAR_DIR = "/shared/.avatars"


class ContactUpsertRequest(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = ""
    projects: Optional[List[str]] = []
    tags: Optional[List[str]] = []
    files: Optional[List[str]] = []


def _contact_to_dict(contact: Contact, db) -> dict:
    d = {
        "id": contact.id,
        "name": contact.name,
        "email": contact.email,
        "phone": contact.phone,
        "company": contact.company,
        "role": contact.role,
        "description": contact.description,
        "notes": contact.notes,
        "projects": [
            r.project_name
            for r in db.query(ContactProject)
            .filter(ContactProject.contact_id == contact.id)
            .all()
        ],
        "tags": [
            r.tag
            for r in db.query(ContactTag)
            .filter(ContactTag.contact_id == contact.id)
            .all()
        ],
        "files": [
            r.file
            for r in db.query(ContactFile)
            .filter(ContactFile.contact_id == contact.id)
            .all()
        ],
    }
    return d


def _insert_junctions(contact_id: str, projects, tags, files, db):
    for p in projects or []:
        db.add(ContactProject(contact_id=contact_id, project_name=p))
    for t in tags or []:
        db.add(ContactTag(contact_id=contact_id, tag=t))
    for f in files or []:
        db.add(ContactFile(contact_id=contact_id, file=f))


def _delete_junctions(contact_id: str, db):
    db.query(ContactProject).filter(ContactProject.contact_id == contact_id).delete()
    db.query(ContactTag).filter(ContactTag.contact_id == contact_id).delete()
    db.query(ContactFile).filter(ContactFile.contact_id == contact_id).delete()


@router.get("/contacts")
async def list_contacts(search: str = None):
    db = get_db()
    try:
        q = db.query(Contact)
        if search:
            pattern = f"%{search}%"
            q = q.filter(
                or_(
                    Contact.name.like(pattern),
                    Contact.email.like(pattern),
                    Contact.company.like(pattern),
                    Contact.role.like(pattern),
                    Contact.description.like(pattern),
                    Contact.notes.like(pattern),
                )
            )
        contacts = q.order_by(Contact.name).all()
        return [
            {
                "id": c.id,
                "name": c.name,
                "email": c.email,
                "phone": c.phone,
                "company": c.company,
                "role": c.role,
                "description": c.description,
                "notes": c.notes,
            }
            for c in contacts
        ]
    except Exception as e:
        logging.error(f"Error listing contacts: {str(e)}")
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error listing contacts: {str(e)}")
    finally:
        db.close()


@router.get("/contacts_of/{file:path}")
async def get_contacts_of_file(file: str):
    db = get_db()
    try:
        contacts = (
            db.query(Contact)
            .join(ContactFile, ContactFile.contact_id == Contact.id)
            .filter(ContactFile.file == file)
            .all()
        )
        return [
            {
                "id": c.id,
                "name": c.name,
                "email": c.email,
                "phone": c.phone,
                "company": c.company,
                "role": c.role,
            }
            for c in contacts
        ]
    except Exception as e:
        logging.error(f"Error retrieving contacts for file {file}: {str(e)}")
        logging.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving contacts for file {file}: {str(e)}",
        )
    finally:
        db.close()


@router.get("/contacts/{contact_id}")
async def get_contact(contact_id: str):
    db = get_db()
    try:
        contact = db.query(Contact).filter(Contact.id == contact_id).first()
        if not contact:
            raise HTTPException(status_code=404, detail=f"Contact {contact_id} not found.")
        return _contact_to_dict(contact, db)
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(f"Error retrieving contact {contact_id}: {str(e)}")
        logging.error(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"Error retrieving contact {contact_id}: {str(e)}"
        )
    finally:
        db.close()


@router.post("/contacts")
async def create_contact(contact: ContactUpsertRequest):
    db = get_db()
    try:
        new_contact = Contact(
            name=contact.name,
            email=contact.email,
            phone=contact.phone,
            company=contact.company,
            role=contact.role,
            description=contact.description,
            notes=contact.notes or "",
        )
        db.add(new_contact)
        db.flush()
        _insert_junctions(new_contact.id, contact.projects, contact.tags, contact.files, db)
        db.commit()
        return {"message": "Contact created successfully.", "id": new_contact.id}
    except Exception as e:
        db.rollback()
        logging.error(f"Error creating contact: {str(e)}")
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error creating contact: {str(e)}")
    finally:
        db.close()


@router.put("/contacts/{contact_id}")
async def update_contact(contact_id: str, contact: ContactUpsertRequest):
    db = get_db()
    try:
        existing = db.query(Contact).filter(Contact.id == contact_id).first()
        if not existing:
            raise HTTPException(status_code=404, detail=f"Contact {contact_id} not found.")
        existing.name = contact.name
        existing.email = contact.email
        existing.phone = contact.phone
        existing.company = contact.company
        existing.role = contact.role
        existing.description = contact.description
        existing.notes = contact.notes or ""
        _delete_junctions(contact_id, db)
        _insert_junctions(contact_id, contact.projects, contact.tags, contact.files, db)
        db.commit()
        return {"message": "Contact updated successfully."}
    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        logging.error(f"Error updating contact {contact_id}: {str(e)}")
        logging.error(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"Error updating contact {contact_id}: {str(e)}"
        )
    finally:
        db.close()


@router.delete("/contacts/{contact_id}")
async def delete_contact(contact_id: str):
    db = get_db()
    try:
        contact = db.query(Contact).filter(Contact.id == contact_id).first()
        if not contact:
            raise HTTPException(status_code=404, detail=f"Contact {contact_id} not found.")
        _delete_junctions(contact_id, db)
        db.delete(contact)
        db.commit()
        return {"message": "Contact deleted successfully."}
    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        logging.error(f"Error deleting contact {contact_id}: {str(e)}")
        logging.error(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"Error deleting contact {contact_id}: {str(e)}"
        )
    finally:
        db.close()


@router.post("/contact/{contact_id}/notes")
async def set_contact_notes(contact_id: str, notes: str):
    db = get_db()
    try:
        contact = db.query(Contact).filter(Contact.id == contact_id).first()
        if not contact:
            raise HTTPException(status_code=404, detail=f"Contact {contact_id} not found.")
        contact.notes = notes
        db.commit()
        return {"message": "Notes updated successfully."}
    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        logging.error(f"Error setting notes for contact {contact_id}: {str(e)}")
        logging.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error setting notes for contact {contact_id}: {str(e)}",
        )
    finally:
        db.close()


@router.post("/contact/{contact_id}/file")
async def add_file_to_contact(contact_id: str, file: str):
    db = get_db()
    try:
        contact = db.query(Contact).filter(Contact.id == contact_id).first()
        if not contact:
            raise HTTPException(status_code=404, detail=f"Contact {contact_id} not found.")
        existing = (
            db.query(ContactFile)
            .filter(ContactFile.contact_id == contact_id, ContactFile.file == file)
            .first()
        )
        if not existing:
            db.add(ContactFile(contact_id=contact_id, file=file))
            db.commit()
        return {"message": "File linked to contact."}
    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        logging.error(f"Error linking file to contact {contact_id}: {str(e)}")
        logging.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error linking file to contact {contact_id}: {str(e)}",
        )
    finally:
        db.close()


@router.delete("/contact/{contact_id}/file")
async def remove_file_from_contact(contact_id: str, file: str):
    db = get_db()
    try:
        db.query(ContactFile).filter(
            ContactFile.contact_id == contact_id, ContactFile.file == file
        ).delete()
        db.commit()
        return {"message": "File unlinked from contact."}
    except Exception as e:
        db.rollback()
        logging.error(f"Error unlinking file from contact {contact_id}: {str(e)}")
        logging.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error unlinking file from contact {contact_id}: {str(e)}",
        )
    finally:
        db.close()


@router.post("/contact/{contact_id}/tag")
async def add_tag_to_contact(contact_id: str, tag: str):
    db = get_db()
    try:
        contact = db.query(Contact).filter(Contact.id == contact_id).first()
        if not contact:
            raise HTTPException(status_code=404, detail=f"Contact {contact_id} not found.")
        existing = (
            db.query(ContactTag)
            .filter(ContactTag.contact_id == contact_id, ContactTag.tag == tag)
            .first()
        )
        if not existing:
            db.add(ContactTag(contact_id=contact_id, tag=tag))
            db.commit()
        return {"message": "Tag added to contact."}
    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        logging.error(f"Error adding tag to contact {contact_id}: {str(e)}")
        logging.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error adding tag to contact {contact_id}: {str(e)}",
        )
    finally:
        db.close()


@router.delete("/contact/{contact_id}/tag")
async def remove_tag_from_contact(contact_id: str, tag: str):
    db = get_db()
    try:
        db.query(ContactTag).filter(
            ContactTag.contact_id == contact_id, ContactTag.tag == tag
        ).delete()
        db.commit()
        return {"message": "Tag removed from contact."}
    except Exception as e:
        db.rollback()
        logging.error(f"Error removing tag from contact {contact_id}: {str(e)}")
        logging.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error removing tag from contact {contact_id}: {str(e)}",
        )
    finally:
        db.close()


@router.post("/contact/{contact_id}/project")
async def add_project_to_contact(contact_id: str, project: str):
    db = get_db()
    try:
        contact = db.query(Contact).filter(Contact.id == contact_id).first()
        if not contact:
            raise HTTPException(status_code=404, detail=f"Contact {contact_id} not found.")
        existing = (
            db.query(ContactProject)
            .filter(
                ContactProject.contact_id == contact_id,
                ContactProject.project_name == project,
            )
            .first()
        )
        if not existing:
            db.add(ContactProject(contact_id=contact_id, project_name=project))
            db.commit()
        return {"message": "Project added to contact."}
    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        logging.error(f"Error adding project to contact {contact_id}: {str(e)}")
        logging.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error adding project to contact {contact_id}: {str(e)}",
        )
    finally:
        db.close()


@router.delete("/contact/{contact_id}/project")
async def remove_project_from_contact(contact_id: str, project: str):
    db = get_db()
    try:
        db.query(ContactProject).filter(
            ContactProject.contact_id == contact_id,
            ContactProject.project_name == project,
        ).delete()
        db.commit()
        return {"message": "Project removed from contact."}
    except Exception as e:
        db.rollback()
        logging.error(f"Error removing project from contact {contact_id}: {str(e)}")
        logging.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error removing project from contact {contact_id}: {str(e)}",
        )
    finally:
        db.close()


@router.post("/contact/{contact_id}/photo")
async def upload_contact_photo(contact_id: str, photo: UploadFile):
    db = get_db()
    try:
        contact = db.query(Contact).filter(Contact.id == contact_id).first()
        if not contact:
            raise HTTPException(status_code=404, detail=f"Contact {contact_id} not found.")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

    content = await photo.read()
    try:
        img = Image.open(BytesIO(content)).convert("RGB")
        img.thumbnail((256, 256), Image.LANCZOS)
        os.makedirs(AVATAR_DIR, exist_ok=True)
        path = os.path.join(AVATAR_DIR, f"{contact_id}.jpg")
        img.save(path, format="JPEG", quality=80, optimize=True)
    except Exception as e:
        logging.error(f"Error processing photo for contact {contact_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid image: {str(e)}")

    return {"message": "Photo uploaded successfully."}


@router.get("/contact/{contact_id}/photo")
async def get_contact_photo(contact_id: str):
    path = os.path.join(AVATAR_DIR, f"{contact_id}.jpg")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="No photo for this contact.")
    return FileResponse(path, media_type="image/jpeg")

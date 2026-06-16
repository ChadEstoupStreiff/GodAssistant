import logging
import traceback

from db import PinnedFile, get_db
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/pinned", tags=["Pinned Files"])


@router.get("")
async def list_pinned():
    db = get_db()
    try:
        return [row.file for row in db.query(PinnedFile).all()]
    except Exception as e:
        logging.error(f"Error listing pinned files: {str(e)}")
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/is_pinned")
async def is_pinned(file: str):
    db = get_db()
    try:
        return db.query(PinnedFile).filter(PinnedFile.file == file).first() is not None
    except Exception as e:
        logging.error(f"Error checking pin status: {str(e)}")
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("")
async def pin_file(file: str):
    db = get_db()
    try:
        if db.query(PinnedFile).filter(PinnedFile.file == file).first() is None:
            db.add(PinnedFile(file=file))
            db.commit()
    except Exception as e:
        db.rollback()
        logging.error(f"Error pinning file: {str(e)}")
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.delete("")
async def unpin_file(file: str):
    db = get_db()
    try:
        row = db.query(PinnedFile).filter(PinnedFile.file == file).first()
        if row:
            db.delete(row)
            db.commit()
    except Exception as e:
        db.rollback()
        logging.error(f"Error unpinning file: {str(e)}")
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

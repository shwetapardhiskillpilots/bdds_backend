from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import images, s_report, sk_report
from auth import get_current_user
import os
import shutil
from datetime import datetime

router = APIRouter()

MEDIA_ROOT = "media"

def save_upload_file(upload_file: UploadFile, destination: str) -> str:
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    with open(destination, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    return destination.replace(MEDIA_ROOT + "/", "")

@router.post("/imageapi")
async def upload_media(
    id: int = Form(...),
    im_vi: list[UploadFile] = File(None),
    special_reports: list[UploadFile] = File(None),
    sketch_scences: list[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    
    if im_vi:
        for file in im_vi:
            ext = os.path.splitext(file.filename)[1]
            status = 1 if ext.lower() in ['.mp4', '.avi', '.mov', '.mkv'] else 0
            rel_path = f"file/image1/{timestamp}{ext}"
            abs_path = os.path.join(MEDIA_ROOT, rel_path)
            save_upload_file(file, abs_path)
            db.add(images(form_id=id, im_vi=rel_path, status=status))
            
    if special_reports:
        for file in special_reports:
            ext = os.path.splitext(file.filename)[1]
            rel_path = f"file/image2/{timestamp}_{file.filename}"
            abs_path = os.path.join(MEDIA_ROOT, rel_path)
            save_upload_file(file, abs_path)
            db.add(s_report(form_id=id, special_report=rel_path))

    if sketch_scences:
        for file in sketch_scences:
            ext = os.path.splitext(file.filename)[1]
            rel_path = f"file/image3/{timestamp}{ext}"
            abs_path = os.path.join(MEDIA_ROOT, rel_path)
            save_upload_file(file, abs_path)
            db.add(sk_report(form_id=id, sketch_scence=rel_path))

    await db.commit()
    return {'status': 200, 'msg': 'all document upload successfully'}

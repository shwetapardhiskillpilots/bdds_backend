from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from database import get_db
from models import AuthUser, AuthToken, Nlogines_creations
from auth import get_current_user
import secrets

router = APIRouter()

@router.post("/login/")
@router.post("/logine/")
async def login(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        data = await request.json()
    except:
        form_data = await request.form()
        data = dict(form_data)
    
    username = data.get('username') or data.get('Mobile_No') or data.get('mobile')
    password = data.get('password')
    
    if not username:
        raise HTTPException(status_code=400, detail="Username required")
        
    result = await db.execute(select(AuthUser).where(AuthUser.username == username))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=400, detail="User not found")
    
    # Mirroring Token behavior
    token_result = await db.execute(select(AuthToken).where(AuthToken.user_id == user.id))
    token = token_result.scalar_one_or_none()
    
    if not token:
        token_key = secrets.token_hex(20)
        token = AuthToken(key=token_key, user_id=user.id)
        db.add(token)
        await db.commit()
    else:
        token_key = token.key

    return {
        'token': token_key,
        'user_id': user.id,
        'email': user.email,
        'Mobile_No': user.username,
        'User_Name': user.first_name,
        'status': 200,
    }

@router.post("/logoutapi")
@router.get("/logoutapi")
async def logout(db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    # Delete token
    await db.execute(delete(AuthToken).where(AuthToken.user_id == current_user.id))
    await db.commit()
    return {"status": 200, "message": "successfully logout"}

@router.get("/profile/")
@router.post("/profile/")
async def get_profile(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    # Fetch additional info from Nlogines_creations
    lc_result = await db.execute(
        select(Nlogines_creations).where(Nlogines_creations.user_id == current_user.id)
    )
    lc = lc_result.scalar_one_or_none()

    # If POST, process updates
    if request.method == "POST":
        try:
            data = await request.json()
        except:
            form_data = await request.form()
            data = dict(form_data)
        
        # Update AuthUser fields
        if 'first_name' in data: current_user.first_name = data['first_name']
        if 'last_name' in data: current_user.last_name = data['last_name']
        if 'email' in data: current_user.email = data['email']
        
        # Update or create Nlogines_creations record
        if 'designation' in data:
            if not lc:
                lc = Nlogines_creations(user_id=current_user.id, l_designation=data['designation'])
                db.add(lc)
            else:
                lc.l_designation = data['designation']
        
        await db.commit()
        # Re-attach to session if it came from cache
        db.add(current_user)
        await db.refresh(current_user)
        if lc: 
            db.add(lc)
            await db.refresh(lc)

    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "is_active": bool(current_user.is_active),
        "is_superuser": bool(current_user.is_superuser),
        "designation": lc.l_designation if lc else "N/A",
        "post": "N/A", # Simplified consistent with admin.py
        "status": 200
    }

@router.post("/testapi")
@router.get("/testapi")
async def test_api():
    return {"msg": "Connection successful", "status": 200}

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from database import get_db
from models import AuthUser, AuthToken, Nlogines_creations, N_degignation, N_post
from auth import get_current_user
from datetime import datetime
import secrets
from passlib.context import CryptContext

# Django uses pbkdf2_sha256 by default
pwd_context = CryptContext(schemes=["django_pbkdf2_sha256"], deprecated="auto")

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
        raise HTTPException(status_code=400, detail="Invalid username or password")
        
    if not password:
        raise HTTPException(status_code=400, detail="Password required")
        
    # Verify the password against Django's hash
    try:
        is_valid = pwd_context.verify(password, user.password)
    except Exception as e:
        # Fallback if the hash format isn't recognized or is corrupted
        is_valid = False
        
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid username or password")
    
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
        
        # Update AuthUser fields using explicit update statement
        from sqlalchemy import update
        update_data = {}
        if 'first_name' in data: update_data['first_name'] = data['first_name']
        if 'last_name' in data: update_data['last_name'] = data['last_name']
        if 'email' in data: update_data['email'] = data['email']
        
        if update_data:
            await db.execute(update(AuthUser).where(AuthUser.id == current_user.id).values(**update_data))
            for k, v in update_data.items():
                setattr(current_user, k, v)
        
        # Update or create Nlogines_creations record
        if 'designation' in data or 'post' in data:
            if not lc:
                lc = Nlogines_creations(user_id=current_user.id)
                db.add(lc)
            if 'designation' in data:
                lc.l_designation = data['designation']
            if 'post' in data and data['post']:
                post_str = data['post']
                post_res = await db.execute(select(N_post).where(N_post.p_post == post_str))
                post_obj = post_res.scalar_one_or_none()
                if not post_obj:
                    post_obj = N_post(p_post=post_str)
                    db.add(post_obj)
                    await db.commit()
                    await db.refresh(post_obj)
                lc.post_id = post_obj.id
        
        await db.commit()
        
        if lc: 
            await db.refresh(lc)

    # Fetch post name
    post_name = "N/A"
    if lc and getattr(lc, 'post_id', None):
        post_res = await db.execute(select(N_post).where(N_post.id == lc.post_id))
        post_obj = post_res.scalar_one_or_none()
        if post_obj:
            post_name = post_obj.p_post

    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "is_active": bool(current_user.is_active),
        "is_superuser": bool(current_user.is_superuser),
        "permission_edit": bool(lc.permission_edit) if lc else False,
        "permission_delete": bool(lc.permission_delete) if lc else False,
        "designation": lc.l_designation if lc else "N/A",
        "post": post_name,
        "status": 200
    }

@router.post("/clogin")
async def login_creation(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        data = await request.json()
    except:
        form_data = await request.form()
        data = dict(form_data)
    
    user_name = data.get('user_name')
    user_number = data.get('u_number')
    user_email = data.get('u_email')
    user_password = data.get('u_password')
    user_designation = data.get('designation')
    user_edit_permission = int(data.get('edit_permission', 0))
    user_dlt_permission = int(data.get('delete_permission', 0))
    station_id = data.get('p_post')

    # Simple validation
    if not user_name or not user_number or not user_password:
        raise HTTPException(status_code=400, detail="Missing required fields")

    # Check if user already exists
    existing = await db.execute(select(AuthUser).where(AuthUser.username == user_number))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Mobile Number Already Present")

    # Fetch designation name for legacy compatibility
    designation_name = ""
    if user_designation:
        deg_res = await db.execute(select(N_degignation).where(N_degignation.id == int(user_designation)))
        deg_obj = deg_res.scalar_one_or_none()
        if deg_obj:
            designation_name = deg_obj.d_designation

    try:
        # Create AuthUser
        new_user = AuthUser(
            username=user_number,
            email=user_email,
            first_name=user_name,
            last_name=str(user_designation), # Mirroring Django's behavior of storing ID as last_name
            password=pwd_context.hash(user_password),
            is_active=1,
            is_staff=0,
            is_superuser=0,
            date_joined=datetime.utcnow()
        )
        db.add(new_user)
        await db.flush()

        # Create Nlogines_creations
        user_data = Nlogines_creations(
            user_id=new_user.id,
            l_numbers=user_number,
            l_designation=designation_name, # Store the actual name string
            join_designation_id=int(user_designation) if user_designation else None,
            permission_edit=user_edit_permission,
            permission_delete=user_dlt_permission,
            post_id=int(station_id) if station_id else None
        )
        db.add(user_data)
        await db.commit()
        
        return {"status": 200, "message": "User created Successfully"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/pwd_update")
async def password_update(request: Request, db: AsyncSession = Depends(get_db)):
    """Mirror Django's forget_passwd: reset password by mobile + email."""
    try:
        data = await request.json()
    except:
        form_data = await request.form()
        data = dict(form_data)

    user_number = data.get('user_number')
    user_email = data.get('user_email')
    password1 = data.get('user_password1')
    password2 = data.get('user_password2')

    if not user_number or not user_email or not password1:
        raise HTTPException(status_code=400, detail="All fields are required")
    if password1 != password2:
        raise HTTPException(status_code=400, detail="Passwords do NOT match")

    result = await db.execute(
        select(AuthUser).where(AuthUser.username == user_number, AuthUser.email == user_email)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Please Insert Correct Mobile Number and Email Id")

    user.password = pwd_context.hash(password1)  # Hash it instead of plain text
    await db.commit()
    return {"status": 200, "message": "Password Update successfully"}

@router.post("/dltuser")
async def delete_user(request: Request, db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    """Mirror Django's dlt_user: delete a user by ID."""
    try:
        data = await request.json()
    except:
        form_data = await request.form()
        data = dict(form_data)

    user_id = data.get('user_id')
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")

    # Delete associated login_creation record first
    lc_result = await db.execute(select(Nlogines_creations).where(Nlogines_creations.user_id == int(user_id)))
    lc = lc_result.scalar_one_or_none()
    if lc:
        await db.delete(lc)

    # Delete auth tokens
    token_result = await db.execute(select(AuthToken).where(AuthToken.user_id == int(user_id)))
    token = token_result.scalar_one_or_none()
    if token:
        await db.delete(token)

    # Delete user
    user_result = await db.execute(select(AuthUser).where(AuthUser.id == int(user_id)))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(user)
    await db.commit()
    return {"status": 200, "message": "successfully user deleted"}

@router.post("/testapi")
@router.get("/testapi")
async def test_api():
    return {"msg": "Connection successful", "status": 200}

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Numeric, Table
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

# Association table for Many-to-Many relationship between Form_data and N_dalam
form_dalam_association = Table(
    'bdds_dashboard_form_data_fdalam',
    Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('form_data_id', Integer, ForeignKey('bdds_dashboard_form_data.id')),
    Column('n_dalam_id', Integer, ForeignKey('bdds_dashboard_n_dalam.id'))
)

class N_location(Base):
    __tablename__ = 'bdds_dashboard_n_location'
    id = Column(Integer, primary_key=True, index=True)
    l_location = Column(String(200))
    l_datetime = Column(DateTime, default=datetime.utcnow)

class N_juridiction(Base):
    __tablename__ = 'bdds_dashboard_n_juridiction'
    id = Column(Integer, primary_key=True, index=True)
    l_juridiction = Column(String(200))
    l_datetime = Column(DateTime, default=datetime.utcnow)

class N_incident(Base):
    __tablename__ = 'bdds_dashboard_n_incident'
    id = Column(Integer, primary_key=True, index=True)
    i_incident = Column(String(200))
    i_datetime = Column(DateTime, default=datetime.utcnow)

class N_weight(Base):
    __tablename__ = 'bdds_dashboard_n_weight'
    id = Column(Integer, primary_key=True, index=True)
    w_weight = Column(String(200))
    w_datetime = Column(DateTime, default=datetime.utcnow)

class N_explosive(Base):
    __tablename__ = 'bdds_dashboard_n_explosive'
    id = Column(Integer, primary_key=True, index=True)
    e_explosive = Column(String(200))
    e_datetime = Column(DateTime, default=datetime.utcnow)

class N_assused(Base):
    __tablename__ = 'bdds_dashboard_n_assused'
    id = Column(Integer, primary_key=True, index=True)
    a_assused = Column(String(200))
    a_datetime = Column(DateTime, default=datetime.utcnow)

class N_dalam(Base):
    __tablename__ = 'bdds_dashboard_n_dalam'
    id = Column(Integer, primary_key=True, index=True)
    d_dalam = Column(String(200))
    d_datetime = Column(DateTime, default=datetime.utcnow)

class N_ditection(Base):
    __tablename__ = 'bdds_dashboard_n_ditection'
    id = Column(Integer, primary_key=True, index=True)
    d_ditection = Column(String(200))
    di_datetime = Column(DateTime, default=datetime.utcnow)

class N_dispose(Base):
    __tablename__ = 'bdds_dashboard_n_dispose'
    id = Column(Integer, primary_key=True, index=True)
    d_dispose = Column(String(200))
    ds_datetime = Column(DateTime, default=datetime.utcnow)

class N_degignation(Base):
    __tablename__ = 'bdds_dashboard_n_degignation'
    id = Column(Integer, primary_key=True, index=True)
    d_designation = Column(String(200))
    d_datetime = Column(DateTime, default=datetime.utcnow)

class N_post(Base):
    __tablename__ = 'bdds_dashboard_n_post'
    id = Column(Integer, primary_key=True, index=True)
    p_post = Column(String(200))
    p_datetime = Column(DateTime, default=datetime.utcnow)

class Nsp_authourity(Base):
    __tablename__ = 'bdds_dashboard_nsp_authourity'
    id = Column(Integer, primary_key=True, index=True)
    s_name = Column(String(200))
    s_numbers = Column(String(200))
    s_designation = Column(String(200))
    s_email = Column(String(256))
    s_password = Column(String(200))
    s_datetime = Column(DateTime, default=datetime.utcnow)

class Form_data(Base):
    __tablename__ = 'bdds_dashboard_form_data'
    id = Column(Integer, primary_key=True, index=True)
    fserial = Column(String(200))
    d_bomb = Column(String(200))
    fdate = Column(DateTime)
    flocation = Column(String(200))
    flocation_type_id = Column(Integer, ForeignKey('bdds_dashboard_n_location.id'))
    flocation_description = Column(Text)
    fjuridiction_id = Column(Integer, ForeignKey('bdds_dashboard_n_juridiction.id'))
    fincident_id = Column(Integer, ForeignKey('bdds_dashboard_n_incident.id'))
    fweight_data_id = Column(Integer, ForeignKey('bdds_dashboard_n_weight.id'))
    fexplosive_id = Column(Integer, ForeignKey('bdds_dashboard_n_explosive.id'))
    fdetonator = Column(String(200))
    fswitch = Column(Text)
    ftarget = Column(String(200))
    fdistruction = Column(Text)
    fassume = Column(Text)
    radio_data = Column(String(200))
    fir = Column(String(200))
    latitude = Column(Numeric(12, 9))
    longitude = Column(Numeric(12, 9))
    flearning = Column(Text)
    fassume_status_new_id = Column(Integer, ForeignKey('bdds_dashboard_n_assused.id'))
    mode_of_detection_id = Column(Integer, ForeignKey('bdds_dashboard_n_ditection.id'))
    detected_description = Column(Text)
    detected_pname = Column(String(200))
    detcted_contact = Column(String(200))
    detected_dispose_id = Column(Integer, ForeignKey('bdds_dashboard_n_dispose.id'))
    dispose_name = Column(String(200))
    dispose_contact = Column(String(200))
    edit_request = Column(Integer, default=0)
    delete_request = Column(Integer, default=0)
    user_id = Column(Integer, ForeignKey('auth_user.id'))
    is_public = Column(Integer, default=0) # 1 for reports from Public Awareness App

    fdalam = relationship("N_dalam", secondary=form_dalam_association)

class images(Base):
    __tablename__ = 'bdds_dashboard_images'
    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(Integer, ForeignKey('bdds_dashboard_form_data.id'))
    im_vi = Column(String(255))
    status = Column(Integer)

class s_report(Base):
    __tablename__ = 'bdds_dashboard_s_report'
    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(Integer, ForeignKey('bdds_dashboard_form_data.id'))
    special_report = Column(String(255))

class sk_report(Base):
    __tablename__ = 'bdds_dashboard_sk_report'
    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(Integer, ForeignKey('bdds_dashboard_form_data.id'))
    sketch_scence = Column(String(255))

class death_person(Base):
    __tablename__ = 'bdds_dashboard_death_person'
    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(Integer, ForeignKey('bdds_dashboard_form_data.id'))
    death_name = Column(String(200))
    death_contact = Column(String(200))

class injured_person(Base):
    __tablename__ = 'bdds_dashboard_injured_person'
    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(Integer, ForeignKey('bdds_dashboard_form_data.id'))
    injured_name = Column(String(200))
    injured_contact = Column(String(200))

class exploded(Base):
    __tablename__ = 'bdds_dashboard_exploded'
    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(Integer, ForeignKey('bdds_dashboard_form_data.id'))
    exploded_name = Column(String(200))
    explode_contact = Column(String(200))

class AuthUser(Base):
    __tablename__ = 'auth_user'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(150), unique=True)
    email = Column(String(254))
    first_name = Column(String(150))
    last_name = Column(String(150))
    password = Column(String(128))
    is_active = Column(Integer)
    is_staff = Column(Integer, default=0)
    is_superuser = Column(Integer, default=0)
    date_joined = Column(DateTime, default=datetime.utcnow)

class Nlogines_creations(Base):
    __tablename__ = 'bdds_dashboard_nlogines_creations'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('auth_user.id'), unique=True)
    l_numbers = Column(String(200))
    l_designation = Column(String(200))
    permission_edit = Column(Integer, default=0)
    permission_delete = Column(Integer, default=0)
    join_designation_id = Column(Integer, ForeignKey('bdds_dashboard_n_degignation.id'))
    post_id = Column(Integer, ForeignKey('bdds_dashboard_n_post.id'))

    user = relationship("AuthUser", backref="login_creation")

class AuthToken(Base):
    __tablename__ = 'authtoken_token'
    key = Column(String(40), primary_key=True)
    user_id = Column(Integer, ForeignKey('auth_user.id'), unique=True)
    created = Column(DateTime, default=datetime.utcnow)

    user = relationship("AuthUser", backref="auth_token")

class CriminalDossier(Base):
    __tablename__ = 'bdds_investigation_dossier'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), index=True)
    alias = Column(String(200))
    description = Column(Text)
    photo_path = Column(String(255))
    status = Column(String(50), default='Active') # Active, Incarcerated, Deceased, etc.
    created_at = Column(DateTime, default=datetime.utcnow)

class CriminalLink(Base):
    __tablename__ = 'bdds_investigation_link'
    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(Integer, ForeignKey('bdds_dashboard_form_data.id'))
    criminal_id = Column(Integer, ForeignKey('bdds_investigation_dossier.id'))
    role = Column(String(50)) # Suspect, Accused, Witness
    created_at = Column(DateTime, default=datetime.utcnow)

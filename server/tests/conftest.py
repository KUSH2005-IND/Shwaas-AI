"""Isolate legacy integration tests from real SQLite records and destructive seeds."""
import json
import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from server.db import Base, User, Screening, Referral, get_db
from server.auth import hash_password
from server.main import app

@pytest.fixture(scope='session')
def legacy_hash(): return hash_password('asha123')

@pytest.fixture(autouse=True)
def legacy_test_database(legacy_hash):
    engine=create_engine('sqlite://',poolclass=StaticPool,connect_args={'check_same_thread':False})
    Base.metadata.create_all(engine);factory=sessionmaker(bind=engine)
    with factory() as db:
        db.add_all([User(id=1,username='asha_rani',role='worker',phc_center='Test PHC',hashed_password=legacy_hash),
                    User(id=2,username='test_doctor',role='doctor',phc_center='Test PHC',hashed_password=legacy_hash)])
        db.flush()
        for i in range(30):
            sid=str(uuid.uuid4());db.add(Screening(id=sid,user_id=1,patient_code=f'TEST-{i}',age=40,sex='female',village='Rampur',
                answers_json=json.dumps({'cough_duration':2}),clinical_score=2,audio_raw_score=.4,audio_calibrated_score=.3,
                tier='MODERATE',pathway_code='PHC_EVALUATION',recommended_pathway='Synthetic test record',consent_given=True))
            db.flush();db.add(Referral(screening_id=sid,status='pending'))
        db.commit()
    def dependency():
        with factory() as db:yield db
    app.dependency_overrides[get_db]=dependency
    yield
    app.dependency_overrides.clear();engine.dispose()

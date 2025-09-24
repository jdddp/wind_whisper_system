from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from datetime import date, datetime

class TurbineCreate(BaseModel):
    farm_name: str
    unit_id: str
    model: Optional[str] = None
    owner_company: Optional[str] = None
    install_date: Optional[date] = None
    status: Optional[str] = 'Normal'  # Normal, Watch, Alarm, Maintenance, Unknown
    metadata_json: Optional[Dict[str, Any]] = None

class TurbineUpdate(BaseModel):
    farm_name: Optional[str] = None
    unit_id: Optional[str] = None
    model: Optional[str] = None
    owner_company: Optional[str] = None
    install_date: Optional[date] = None
    status: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None

class TurbineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    turbine_id: str
    farm_name: str
    unit_id: str
    model: Optional[str]
    owner_company: Optional[str]
    install_date: Optional[date]
    status: Optional[str]
    metadata_json: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: Optional[datetime]
"""
Delta management routes
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Path
from pydantic import BaseModel

from ..database import (
    get_delta_manager,
    DeltaRecord,
    CreateDeltaRecordInput,
    UpdateDeltaRecordInput,
    DeltaRecordQuery,
    DeltaRecordStats,
    AccountDeltaSummary,
    InstrumentDeltaSummary
)


class DeltaRecordResponse(BaseModel):
    """Delta record response"""
    success: bool
    message: str
    record: Optional[DeltaRecord] = None


class DeltaRecordsResponse(BaseModel):
    """Delta records list response"""
    success: bool
    message: str
    records: List[DeltaRecord]
    total: int


class DeltaStatsResponse(BaseModel):
    """Delta statistics response"""
    success: bool
    message: str
    stats: Optional[DeltaRecordStats] = None


class DeltaSummaryResponse(BaseModel):
    """Delta summary response"""
    success: bool
    message: str
    account_summaries: List[AccountDeltaSummary] = []
    instrument_summaries: List[InstrumentDeltaSummary] = []


delta_router = APIRouter()


@delta_router.post("/api/delta/records", response_model=DeltaRecordResponse)
async def create_delta_record(input_data: CreateDeltaRecordInput):
    """Create new delta record"""
    try:
        delta_manager = get_delta_manager()
        record = await delta_manager.create_record(input_data)
        
        return DeltaRecordResponse(
            success=True,
            message="Delta record created successfully",
            record=record
        )
        
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": str(error)
            }
        )


@delta_router.get("/api/delta/records/{record_id}", response_model=DeltaRecordResponse)
async def get_delta_record(record_id: int = Path(..., description="Record ID")):
    """Get delta record by ID"""
    try:
        delta_manager = get_delta_manager()
        record = await delta_manager.get_record_by_id(record_id)
        
        if not record:
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "message": "Delta record not found"
                }
            )
        
        return DeltaRecordResponse(
            success=True,
            message="Delta record retrieved successfully",
            record=record
        )
        
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": str(error)
            }
        )


@delta_router.put("/api/delta/records/{record_id}", response_model=DeltaRecordResponse)
async def update_delta_record(
    record_id: int,
    input_data: UpdateDeltaRecordInput
):
    """Update delta record"""
    try:
        delta_manager = get_delta_manager()
        record = await delta_manager.update_record(record_id, input_data)
        
        if not record:
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "message": "Delta record not found"
                }
            )
        
        return DeltaRecordResponse(
            success=True,
            message="Delta record updated successfully",
            record=record
        )
        
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": str(error)
            }
        )


@delta_router.delete("/api/delta/records/{record_id}")
async def delete_delta_record(record_id: int = Path(..., description="Record ID")):
    """Delete delta record"""
    try:
        delta_manager = get_delta_manager()
        success = await delta_manager.delete_record(record_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "message": "Delta record not found"
                }
            )
        
        return {
            "success": True,
            "message": "Delta record deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": str(error)
            }
        )


@delta_router.get("/api/delta/records", response_model=DeltaRecordsResponse)
async def query_delta_records(
    account_id: Optional[str] = Query(None, description="Account ID"),
    instrument_name: Optional[str] = Query(None, description="Instrument name"),
    order_id: Optional[str] = Query(None, description="Order ID"),
    tv_id: Optional[int] = Query(None, description="TradingView ID"),
    record_type: Optional[str] = Query(None, description="Record type"),
    limit: Optional[int] = Query(100, description="Limit results")
):
    """Query delta records"""
    try:
        delta_manager = get_delta_manager()
        
        query = DeltaRecordQuery(
            account_id=account_id,
            instrument_name=instrument_name,
            order_id=order_id,
            tv_id=tv_id,
            record_type=record_type
        )
        
        records = await delta_manager.query_records(query, limit)
        
        return DeltaRecordsResponse(
            success=True,
            message=f"Found {len(records)} delta records",
            records=records,
            total=len(records)
        )
        
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": str(error)
            }
        )


@delta_router.get("/api/delta/stats", response_model=DeltaStatsResponse)
async def get_delta_stats():
    """Get delta statistics"""
    try:
        delta_manager = get_delta_manager()
        stats = await delta_manager.get_stats()
        
        return DeltaStatsResponse(
            success=True,
            message="Delta statistics retrieved successfully",
            stats=stats
        )
        
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": str(error)
            }
        )


@delta_router.get("/api/delta/summary", response_model=DeltaSummaryResponse)
async def get_delta_summary(
    account_id: Optional[str] = Query(None, description="Account ID filter"),
    instrument_name: Optional[str] = Query(None, description="Instrument name filter")
):
    """Get delta summary"""
    try:
        delta_manager = get_delta_manager()
        
        account_summaries = await delta_manager.get_account_summary(account_id)
        instrument_summaries = await delta_manager.get_instrument_summary(instrument_name)
        
        return DeltaSummaryResponse(
            success=True,
            message="Delta summary retrieved successfully",
            account_summaries=account_summaries,
            instrument_summaries=instrument_summaries
        )
        
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": str(error)
            }
        )

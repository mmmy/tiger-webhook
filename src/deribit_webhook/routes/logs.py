"""
Log management and query API routes

Provides endpoints for querying, filtering, and managing application logs.
"""

import os
import re
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from pathlib import Path

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field

from ..config import settings
from ..utils.response_utils import format_success_response, format_error_response


# Router setup
logs_router = APIRouter(prefix="/api/logs")


class LogEntry(BaseModel):
    """Log entry model"""
    timestamp: str
    level: str
    logger: str
    message: str
    module: Optional[str] = None
    function: Optional[str] = None
    line: Optional[int] = None
    extra_data: Optional[Dict[str, Any]] = None


class LogQueryParams(BaseModel):
    """Log query parameters"""
    start_time: Optional[str] = Field(None, description="Start time (ISO format or relative like '1h ago')")
    end_time: Optional[str] = Field(None, description="End time (ISO format or relative like 'now')")
    level: Optional[str] = Field(None, description="Log level filter")
    search: Optional[str] = Field(None, description="Search text in messages")
    limit: int = Field(100, description="Maximum number of entries to return")
    offset: int = Field(0, description="Number of entries to skip")


def _normalize_datetime(dt: datetime) -> datetime:
    """Normalize datetimes to UTC naive for consistent comparisons."""
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def parse_relative_time(time_str: str) -> datetime:
    """Parse relative time strings like '1h ago', '30m ago', etc."""
    if time_str.lower() == 'now':
        return datetime.now()
    
    # Pattern for relative time: number + unit + 'ago'
    pattern = r'(\d+)([smhd])\s*ago'
    match = re.match(pattern, time_str.lower())
    
    if not match:
        # Try to parse as ISO format
        try:
            iso_time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            return _normalize_datetime(iso_time)
        except ValueError:
            raise ValueError(f"Invalid time format: {time_str}")
    
    amount, unit = match.groups()
    amount = int(amount)
    
    now = datetime.now()
    if unit == 's':
        return now - timedelta(seconds=amount)
    elif unit == 'm':
        return now - timedelta(minutes=amount)
    elif unit == 'h':
        return now - timedelta(hours=amount)
    elif unit == 'd':
        return now - timedelta(days=amount)
    else:
        raise ValueError(f"Unknown time unit: {unit}")


def parse_text_log_line(line: str) -> LogEntry:
    """Parse log lines that follow the text formatter syntax."""
    pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\s+\[\s*(\w+)\s*\]\s+\[([^\]]+)\]\s+(.+?)(?:\s+\(([^:]+):(\d+)\))?$'
    match = re.match(pattern, line)

    if match:
        timestamp, level, logger, message, module, line_num = match.groups()
        return LogEntry(
            timestamp=timestamp,
            level=level,
            logger=logger,
            message=message,
            module=module,
            line=int(line_num) if line_num else None
        )

    return LogEntry(
        timestamp=datetime.now().isoformat(),
        level='INFO',
        logger='unknown',
        message=line
    )


def parse_log_line(line: str) -> Optional[LogEntry]:
    """Parse a single log line into LogEntry"""
    line = line.strip()
    if not line:
        return None

    try:
        if settings.log_format.lower() == 'json':
            try:
                data = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                return parse_text_log_line(line)
            else:
                return LogEntry(
                    timestamp=data.get('timestamp', ''),
                    level=data.get('level', ''),
                    logger=data.get('logger', ''),
                    message=data.get('message', ''),
                    module=data.get('module'),
                    function=data.get('function'),
                    line=data.get('line'),
                    extra_data={k: v for k, v in data.items()
                               if k not in ['timestamp', 'level', 'logger', 'message', 'module', 'function', 'line']}
                )

        return parse_text_log_line(line)

    except Exception as e:
        return LogEntry(
            timestamp=datetime.now().isoformat(),
            level='ERROR',
            logger='parser',
            message=f"Failed to parse log line: {line} Error: {str(e)}"
        )



def _filter_entries(entries: List[LogEntry], params: LogQueryParams) -> List[LogEntry]:
    """Apply query filters, sorting, and pagination to log entries."""
    filtered_entries: List[LogEntry] = []

    start_time = None
    end_time = None

    try:
        if params.start_time:
            start_time = _normalize_datetime(parse_relative_time(params.start_time))
        if params.end_time:
            end_time = _normalize_datetime(parse_relative_time(params.end_time))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    for entry in entries:
        # Time filter
        if start_time or end_time:
            try:
                entry_time = datetime.fromisoformat(entry.timestamp.replace('Z', '+00:00'))
                entry_time = _normalize_datetime(entry_time)
                if start_time and entry_time < start_time:
                    continue
                if end_time and entry_time > end_time:
                    continue
            except ValueError:
                # If timestamp parsing fails, include the entry
                pass

        # Level filter
        if params.level and entry.level.upper() != params.level.upper():
            continue

        # Search filter
        if params.search and params.search.lower() not in entry.message.lower():
            continue

        filtered_entries.append(entry)

    # Sort by timestamp (newest first)
    filtered_entries.sort(key=lambda x: x.timestamp, reverse=True)

    # Apply pagination
    start_idx = params.offset
    end_idx = start_idx + params.limit

    return filtered_entries[start_idx:end_idx]


def read_log_files(file_paths: List[str], params: LogQueryParams) -> List[LogEntry]:
    """Read and filter multiple log files."""
    aggregated_entries: List[LogEntry] = []

    for file_path in file_paths:
        if not os.path.exists(file_path):
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    entry = parse_log_line(line)
                    if entry:
                        aggregated_entries.append(entry)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Error reading log file {file_path}: {str(exc)}") from exc

    if not aggregated_entries:
        return []

    return _filter_entries(aggregated_entries, params)


def read_log_file(file_path: str, params: LogQueryParams) -> List[LogEntry]:
    """Backward compatible helper to read a single log file."""
    return read_log_files([file_path], params)


def get_log_files_for_query(primary_log_file: str) -> List[str]:
    """Return all matching log files (primary + rotated) for the query."""
    primary_path = Path(primary_log_file)
    log_dir = primary_path.parent if primary_path.parent != Path("") else Path(".")

    if not log_dir.exists():
        return [str(primary_path)] if primary_path.exists() else []

    pattern = f"{primary_path.name}*"
    files = [path for path in log_dir.glob(pattern) if path.is_file()]

    if primary_path.exists() and primary_path not in files:
        files.append(primary_path)

    files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return [str(path) for path in files]


@logs_router.get("/query")
async def query_logs(
    start_time: Optional[str] = Query(None, description="Start time (ISO format or relative like '1h ago')"),
    end_time: Optional[str] = Query(None, description="End time (ISO format or relative like 'now')"),
    level: Optional[str] = Query(None, description="Log level filter (DEBUG, INFO, WARNING, ERROR, CRITICAL)"),
    search: Optional[str] = Query(None, description="Search text in messages"),
    limit: int = Query(100, description="Maximum number of entries to return", ge=1, le=1000),
    offset: int = Query(0, description="Number of entries to skip", ge=0)
):
    """Query logs with filters and pagination"""
    try:
        params = LogQueryParams(
            start_time=start_time,
            end_time=end_time,
            level=level,
            search=search,
            limit=limit,
            offset=offset
        )
        
        # Get log file path(s)
        log_file = settings.log_file or "./logs/combined.log"
        log_files = get_log_files_for_query(log_file)

        # Read and filter logs
        entries = read_log_files(log_files if log_files else [log_file], params)
        
        return format_success_response(
            message=f"Found {len(entries)} log entries",
            data={
                "entries": [entry.dict() for entry in entries],
                "total_returned": len(entries),
                "query_params": params.dict(),
                "log_file": log_file,
                "scanned_files": log_files
            }
        )
        
    except ValueError as e:
        return format_error_response(
            message="Invalid query parameters",
            error=str(e),
            code="INVALID_PARAMS"
        )
    except Exception as e:
        return format_error_response(
            message="Failed to query logs",
            error=str(e),
            code="QUERY_ERROR"
        )


@logs_router.get("/files")
async def list_log_files():
    """List available log files"""
    try:
        log_dir = Path(settings.log_file).parent if settings.log_file else Path("./logs")
        
        if not log_dir.exists():
            return format_success_response(
                message="No log directory found",
                data={"files": [], "log_directory": str(log_dir)}
            )
        
        files = []
        for file_path in log_dir.glob("*.log*"):
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    "name": file_path.name,
                    "path": str(file_path),
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "size_mb": round(stat.st_size / (1024 * 1024), 2)
                })
        
        # Sort by modification time (newest first)
        files.sort(key=lambda x: x['modified'], reverse=True)
        
        return format_success_response(
            message=f"Found {len(files)} log files",
            data={
                "files": files,
                "log_directory": str(log_dir),
                "current_log_file": settings.log_file
            }
        )
        
    except Exception as e:
        return format_error_response(
            message="Failed to list log files",
            error=str(e),
            code="LIST_ERROR"
        )


@logs_router.get("/levels")
async def get_log_levels():
    """Get available log levels"""
    return format_success_response(
        message="Available log levels",
        data={
            "levels": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            "current_level": settings.log_level,
            "descriptions": {
                "DEBUG": "Detailed information for debugging",
                "INFO": "General information messages",
                "WARNING": "Warning messages",
                "ERROR": "Error messages",
                "CRITICAL": "Critical error messages"
            }
        }
    )


@logs_router.get("/stats")
async def get_log_stats():
    """Get log statistics"""
    try:
        log_file = settings.log_file or "./logs/combined.log"
        
        if not os.path.exists(log_file):
            return format_success_response(
                message="No log file found",
                data={"stats": None, "log_file": log_file}
            )
        
        # Read recent logs for statistics
        params = LogQueryParams(start_time="24h ago", limit=10000)
        entries = read_log_file(log_file, params)
        
        # Calculate statistics
        level_counts = {}
        module_counts = {}
        hourly_counts = {}
        
        for entry in entries:
            # Level statistics
            level_counts[entry.level] = level_counts.get(entry.level, 0) + 1
            
            # Module statistics
            if entry.module:
                module_counts[entry.module] = module_counts.get(entry.module, 0) + 1
            
            # Hourly statistics
            try:
                entry_time = datetime.fromisoformat(entry.timestamp.replace('Z', '+00:00'))
                hour_key = entry_time.strftime('%Y-%m-%d %H:00')
                hourly_counts[hour_key] = hourly_counts.get(hour_key, 0) + 1
            except ValueError:
                pass
        
        # File statistics
        file_stat = os.stat(log_file)
        
        return format_success_response(
            message="Log statistics generated",
            data={
                "file_info": {
                    "path": log_file,
                    "size_bytes": file_stat.st_size,
                    "size_mb": round(file_stat.st_size / (1024 * 1024), 2),
                    "modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat()
                },
                "recent_24h": {
                    "total_entries": len(entries),
                    "level_distribution": level_counts,
                    "top_modules": dict(sorted(module_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
                    "hourly_distribution": dict(sorted(hourly_counts.items()))
                }
            }
        )
        
    except Exception as e:
        return format_error_response(
            message="Failed to generate log statistics",
            error=str(e),
            code="STATS_ERROR"
        )

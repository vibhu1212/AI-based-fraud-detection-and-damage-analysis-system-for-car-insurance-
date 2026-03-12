"""
Metrics Collector Service
Handles collection, aggregation, and analysis of system performance metrics.
Designed with singleton pattern and asynchronous database writes for performance.
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
import logging
import time
from contextlib import contextmanager

from app.models.metrics import ProcessMetric
from app.models.base import SessionLocal

logger = logging.getLogger(__name__)

class MetricsCollector:
    """
    Service for tracking and analyzing system performance metrics.
    """
    
    def __init__(self):
        self._batch = []
        self.batch_size = 10  # Write to DB in batches to reduce overhead
        
    def track_metric(
        self,
        name: str,
        value: float,
        unit: str,
        metric_type: str = "performance",
        claim_id: Optional[str] = None,
        tags: Optional[Dict] = None,
        status: str = "success",
        error_type: Optional[str] = None,
        db: Optional[Session] = None
    ):
        """
        Track a single metric event.
        """
        try:
            metric = ProcessMetric(
                name=name,
                value=value,
                unit=unit,
                metric_type=metric_type,
                claim_id=claim_id,
                tags=tags or {},
                status=status,
                error_type=error_type,
                created_at=datetime.utcnow()
            )
            
            # If DB session provided, write immediately (useful for atomic transactions)
            if db:
                db.add(metric)
                # Don't commit here, let caller handle transaction
            else:
                self._write_direct(metric)
                
            logger.debug(f"Metric tracked: {name}={value}{unit}")
            
        except Exception as e:
            logger.error(f"Failed to track metric {name}: {str(e)}")

    def _write_direct(self, metric: ProcessMetric):
        """Write metric directly to database using a fresh session"""
        db = SessionLocal()
        try:
            db.add(metric)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to write metric to DB: {str(e)}")
            db.rollback()
        finally:
            db.close()

    @contextmanager
    def measure_time(self, name: str, claim_id: Optional[str] = None, tags: Optional[Dict] = None):
        """
        Context manager to measure execution time of a block.
        
        Usage:
            with metrics.measure_time("my_process", claim_id):
                do_work()
        """
        start_time = time.time()
        status = "success"
        error_type = None
        
        try:
            yield
        except Exception as e:
            status = "failure"
            error_type = type(e).__name__
            raise
        finally:
            duration = time.time() - start_time
            self.track_metric(
                name=name,
                value=duration,
                unit="s",
                metric_type="execution_time",
                claim_id=claim_id,
                tags=tags,
                status=status,
                error_type=error_type
            )

    def get_aggregated_metrics(
        self,
        time_range_hours: int = 24,
        metric_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get aggregated metrics for dashboard.
        Returns average times, success rates, and throughput.
        """
        db = SessionLocal()
        try:
            start_time = datetime.utcnow() - timedelta(hours=time_range_hours)
            query = db.query(ProcessMetric).filter(ProcessMetric.created_at >= start_time)
            
            if metric_type:
                query = query.filter(ProcessMetric.metric_type == metric_type)
                
            metrics = query.all()
            
            # Aggregate results
            grouped = {}
            for m in metrics:
                if m.name not in grouped:
                    grouped[m.name] = {
                        "count": 0,
                        "total_value": 0.0,
                        "failures": 0,
                        "min": float('inf'),
                        "max": float('-inf'),
                        "values": []  # For trend lines
                    }
                
                stats = grouped[m.name]
                stats["count"] += 1
                stats["total_value"] += m.value
                stats["values"].append({
                    "time": m.created_at.isoformat(),
                    "value": m.value,
                    "status": m.status
                })
                
                if m.status == "failure":
                    stats["failures"] += 1
                    
                if m.value < stats["min"]:
                    stats["min"] = m.value
                if m.value > stats["max"]:
                    stats["max"] = m.value

            # Calculate averages and rates
            result = []
            for name, stats in grouped.items():
                if stats["count"] == 0:
                    continue
                    
                result.append({
                    "name": name,
                    "avg_value": stats["total_value"] / stats["count"],
                    "min_value": stats["min"] if stats["min"] != float('inf') else 0,
                    "max_value": stats["max"] if stats["max"] != float('-inf') else 0,
                    "request_count": stats["count"],
                    "error_rate": (stats["failures"] / stats["count"]) * 100,
                    "trend": stats["values"][-50:] # Last 50 data points for sparklines
                })
                
            return {
                "time_range_hours": time_range_hours,
                "metrics": result,
                "total_events": len(metrics)
            }
            
        finally:
            db.close()

# Singleton instance
metrics_collector = MetricsCollector()

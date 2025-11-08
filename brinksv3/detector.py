import cv2
import numpy as np
from ultralytics import YOLO
import asyncio
from typing import AsyncGenerator
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class YOLODetector:
    """YOLO-based people detector for RTSP streams"""
    
    def __init__(self, model_name: str = "yolov8n.pt"):
        """
        Initialize YOLO detector
        
        Args:
            model_name: YOLO model to use (yolov8n.pt, yolov8s.pt, yolov8m.pt, etc.)
        """
        logger.info(f"Loading YOLO model: {model_name}")
        self.model = YOLO(model_name)
        # Class 0 in COCO dataset is 'person'
        self.person_class_id = 0
        self.active_captures = []
        
    async def count_people_single_frame(
        self, 
        rtsp_url: str, 
        confidence: float = 0.5
    ) -> int:
        """
        Count people in a single frame from RTSP stream
        
        Args:
            rtsp_url: RTSP stream URL
            confidence: Detection confidence threshold
            
        Returns:
            Number of people detected
        """
        cap = None
        try:
            # Open RTSP stream
            cap = cv2.VideoCapture(rtsp_url)
            
            if not cap.isOpened():
                raise Exception(f"Failed to open RTSP stream: {rtsp_url}")
            
            # Read a frame
            ret, frame = cap.read()
            
            if not ret or frame is None:
                raise Exception("Failed to read frame from RTSP stream")
            
            # Run detection
            results = self.model(frame, conf=confidence, verbose=False)
            
            # Count people (class 0 in COCO dataset)
            people_count = 0
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    class_id = int(box.cls[0])
                    if class_id == self.person_class_id:
                        people_count += 1
            
            logger.info(f"Detected {people_count} people in frame")
            return people_count
            
        except Exception as e:
            logger.error(f"Error counting people: {str(e)}")
            raise
        finally:
            if cap is not None:
                cap.release()
    
    async def generate_frames(
        self, 
        rtsp_url: str, 
        confidence: float = 0.5
    ) -> AsyncGenerator[bytes, None]:
        """
        Generate frames from RTSP stream with people detection overlay
        
        Args:
            rtsp_url: RTSP stream URL
            confidence: Detection confidence threshold
            
        Yields:
            JPEG encoded frames with detection overlay
        """
        cap = None
        try:
            # Open RTSP stream
            cap = cv2.VideoCapture(rtsp_url)
            self.active_captures.append(cap)
            
            if not cap.isOpened():
                raise Exception(f"Failed to open RTSP stream: {rtsp_url}")
            
            logger.info(f"Started streaming from: {rtsp_url}")
            
            while True:
                ret, frame = cap.read()
                
                if not ret or frame is None:
                    logger.warning("Failed to read frame, stopping stream")
                    break
                
                # Run detection
                results = self.model(frame, conf=confidence, verbose=False)
                
                # Draw bounding boxes and count people
                people_count = 0
                for result in results:
                    boxes = result.boxes
                    for box in boxes:
                        class_id = int(box.cls[0])
                        
                        if class_id == self.person_class_id:
                            people_count += 1
                            
                            # Get box coordinates
                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            conf = float(box.conf[0])
                            
                            # Draw bounding box
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                            
                            # Draw label
                            label = f"Person {conf:.2f}"
                            cv2.putText(
                                frame, label, (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2
                            )
                
                # Draw people count on frame
                count_text = f"People Count: {people_count}"
                cv2.putText(
                    frame, count_text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2
                )
                
                # Encode frame as JPEG
                ret, buffer = cv2.imencode('.jpg', frame)
                
                if not ret:
                    continue
                
                frame_bytes = buffer.tobytes()
                
                # Yield frame in multipart format
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                
                # Small delay to control frame rate
                await asyncio.sleep(0.03)  # ~30 FPS
                
        except Exception as e:
            logger.error(f"Error in frame generation: {str(e)}")
            raise
        finally:
            if cap is not None:
                cap.release()
                if cap in self.active_captures:
                    self.active_captures.remove(cap)
            logger.info("Stream stopped")
    
    def cleanup(self):
        """Release all video captures"""
        logger.info("Cleaning up resources")
        for cap in self.active_captures:
            if cap is not None and cap.isOpened():
                cap.release()
        self.active_captures.clear()
        cv2.destroyAllWindows()

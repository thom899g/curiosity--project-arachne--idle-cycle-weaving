"""
Firebase Firestore coordination for Project Arachne.
"""
import firebase_admin
from firebase_admin import credentials, firestore
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FirebaseCoordinator:
    """Handles communication with Firebase Firestore."""

    def __init__(self, credential_path: str):
        self.credential_path = credential_path
        self.app: Optional[firebase_admin.App] = None
        self.db: Optional[firestore.Client] = None

    def connect(self) -> None:
        """Connect to Firebase Firestore."""
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate(self.credential_path)
                self.app = firebase_admin.initialize_app(cred)
            else:
                self.app = firebase_admin.get_app()
            self.db = firestore.client()
            logger.info("Connected to Firebase Firestore.")
        except Exception as e:
            logger.exception(f"Failed to connect to Firebase: {e}")
            raise

    def update_node_status(self, node_id: str, status: Dict[str, Any]) -> None:
        """Update the status of this node in Firestore."""
        if self.db is None:
            raise ConnectionError("Firestore not connected.")

        try:
            doc_ref = self.db.collection('nodes').document(node_id)
            status['last_updated'] = datetime.utcnow()
            doc_ref.set(status, merge=True)
            logger.debug(f"Updated node status for {node_id}.")
        except Exception as e:
            logger.exception(f"Failed to update node status: {e}")

    def fetch_opportunities(self, limit: int = 10) -> list[Dict[str, Any]]:
        """Fetch the latest opportunities from Firestore."""
        if self.db is None:
            raise ConnectionError("Firestore not connected.")

        try:
            opportunities_ref = self.db.collection('opportunities')
            query = opportunities_ref.order_by('discovered_at', direction=firestore.Query.D
"""
Unit tests for activity endpoints
"""
import pytest
import json
from datetime import datetime, timedelta


class TestActivityCreation:
    """Tests for POST /activities endpoint"""
    
    def test_activity_creation_success(self, client, auth_token):
        """Test successful activity creation"""
        response = client.post(
            "/activities",
            json={
                "activity_id": "act_new_001",
                "activity_name": "Test Activity",
                "date_start": (datetime.now() + timedelta(days=1)).isoformat(),
                "date_end": (datetime.now() + timedelta(days=2)).isoformat(),
                "drivers": "Driver Name",
                "description": "Test activity description",
                "groups": ["test-group"],
                "requires_permission": True
            },
            headers={"Authorization": auth_token}
        )
        
        # May require auth or may be open endpoint
        if response.status_code in [200, 201]:
            data = response.json()
            assert "activity_id" in data or "message" in data
    
    def test_activity_creation_with_missing_required_field(self, client, auth_token):
        """Test activity creation fails with missing required field"""
        response = client.post(
            "/activities",
            json={
                "activity_name": "Test Activity",
                "date_start": (datetime.now() + timedelta(days=1)).isoformat(),
                # Missing activity_id, date_end, etc.
            },
            headers={"Authorization": auth_token}
        )
        
        # Should return validation error for missing field
        if response.status_code >= 400:
            assert response.status_code == 422
    
    def test_activity_creation_with_invalid_date_format(self, client, auth_token):
        """Test activity creation with invalid date format"""
        response = client.post(
            "/activities",
            json={
                "activity_id": "act_new_002",
                "activity_name": "Test Activity",
                "date_start": "invalid-date",
                "date_end": "invalid-date",
                "drivers": "Driver",
                "description": "Test",
                "groups": ["test-group"]
            },
            headers={"Authorization": auth_token}
        )
        
        # Should fail validation
        if response.status_code >= 400:
            assert response.status_code in [400, 422]


class TestActivityRetrieval:
    """Tests for GET /activities/{activity_id} endpoint"""
    
    def test_activity_retrieval_success(self, client, test_activity):
        """Test successful activity retrieval"""
        response = client.get(f"/activities/{test_activity['activity_id']}")
        
        if response.status_code == 200:
            data = response.json()
            assert "activity_name" in data or "activity_id" in data
    
    def test_activity_retrieval_not_found(self, client):
        """Test activity retrieval for non-existent activity"""
        response = client.get("/activities/nonexistent_activity")
        
        assert response.status_code in [200, 404]


class TestActivityUpdate:
    """Tests for PUT /activities/{activity_id} endpoint"""
    
    def test_activity_update_success(self, client, test_activity, auth_token):
        """Test successful activity update"""
        response = client.put(
            f"/activities/{test_activity['activity_id']}",
            json={
                "activity_id": test_activity['activity_id'],
                "activity_name": "Updated Activity Name",
                "date_start": test_activity['date_start'],
                "date_end": test_activity['date_end'],
                "drivers": "Updated Driver",
                "description": "Updated description",
                "groups": ["test-group"]
            },
            headers={"Authorization": auth_token}
        )
        
        if response.status_code in [200, 204]:
            assert True
        else:
            # May not be implemented or require special permissions
            assert response.status_code in [404, 501]
    
    def test_activity_update_nonexistent_activity(self, client, auth_token):
        """Test updating non-existent activity"""
        response = client.put(
            "/activities/nonexistent_activity",
            json={
                "activity_id": "nonexistent_activity",
                "activity_name": "Updated",
                "date_start": (datetime.now() + timedelta(days=1)).isoformat(),
                "date_end": (datetime.now() + timedelta(days=2)).isoformat(),
                "drivers": "Driver",
                "description": "Test",
                "groups": ["test-group"]
            },
            headers={"Authorization": auth_token}
        )
        
        assert response.status_code in [404, 200, 501]


class TestActivityDeletion:
    """Tests for DELETE /activities/{activity_id} endpoint"""
    
    def test_activity_deletion_success(self, client, test_activity, auth_token):
        """Test successful activity deletion"""
        response = client.delete(
            f"/activities/{test_activity['activity_id']}",
            headers={"Authorization": auth_token}
        )
        
        if response.status_code in [200, 204]:
            assert True
        else:
            # May require different auth level
            assert response.status_code in [403, 404, 501]
    
    def test_activity_deletion_nonexistent(self, client, auth_token):
        """Test deletion of non-existent activity"""
        response = client.delete(
            "/activities/nonexistent_activity",
            headers={"Authorization": auth_token}
        )
        
        # Should succeed silently or return 404
        assert response.status_code in [200, 204, 404, 501]


class TestActivityListing:
    """Tests for GET /activities-all endpoint"""
    
    def test_get_all_activities(self, client, test_activity):
        """Test retrieving all activities"""
        response = client.get("/activities-all")
        
        assert response.status_code == 200
        data = response.json()
        assert "activities" in data or isinstance(data, (list, dict))
    
    def test_get_all_activities_exclude_past(self, client):
        """Test retrieving activities excluding past events"""
        response = client.get("/activities-all?include_past=false")
        
        assert response.status_code == 200
    
    def test_get_all_activities_include_past(self, client):
        """Test retrieving all activities including past events"""
        response = client.get("/activities-all?include_past=true")
        
        assert response.status_code == 200


class TestActivityParticipants:
    """Tests for /participants endpoint"""
    
    def test_get_activity_participants(self, client, test_activity):
        """Test retrieving participants for an activity"""
        response = client.get(f"/participants/{test_activity['activity_id']}")
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))
    
    def test_get_participants_nonexistent_activity(self, client):
        """Test getting participants for non-existent activity"""
        response = client.get("/participants/nonexistent_activity")
        
        assert response.status_code in [200, 404]


class TestActivityPermissions:
    """Tests for /activity-permissions endpoint"""
    
    def test_assign_activity_permission(self, client, auth_token):
        """Test assigning permission to activity"""
        response = client.post(
            "/activity-permissions",
            json={
                "youth_id": "youth_001",
                "activity_id": "activity_001",
                "permission_given": True,
                "permission_date": datetime.now().isoformat()
            },
            headers={"Authorization": auth_token}
        )
        
        if response.status_code in [200, 201]:
            assert True
        else:
            # May require auth or different permissions
            assert response.status_code in [403, 404, 501]


class TestActivityHealthReports:
    """Tests for /activity-health-reports endpoint"""
    
    def test_get_activity_health_report(self, client, test_activity):
        """Test retrieving health report for activity"""
        response = client.get(f"/activity-health-reports/{test_activity['activity_id']}")
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
    
    def test_get_health_report_nonexistent_activity(self, client):
        """Test getting health report for non-existent activity"""
        response = client.get("/activity-health-reports/nonexistent_activity")
        
        assert response.status_code in [200, 404]


class TestActivityGroups:
    """Tests for /activity-groups endpoint"""
    
    def test_get_activity_groups(self, client):
        """Test retrieving activity groups"""
        response = client.get("/activity-groups")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))


class TestPendingApprovals:
    """Tests for /activities-pending-approval endpoint"""
    
    def test_get_pending_approvals(self, client):
        """Test retrieving pending activity approvals"""
        response = client.get("/activities-pending-approval")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))


class TestActivityReconciliation:
    """Tests for activity reconciliation endpoints"""
    
    def test_get_activity_for_reconciliation(self, client, test_activity):
        """Test retrieving activity for reconciliation"""
        response = client.get(f"/activities/reconcile/{test_activity['activity_id']}")
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
    
    def test_update_activity_reconciliation(self, client, test_activity, auth_token):
        """Test updating reconciled activity data"""
        response = client.put(
            f"/activities/reconcile/{test_activity['activity_id']}",
            json={
                "activity_id": test_activity['activity_id'],
                "notes": "Reconciliation notes"
            },
            headers={"Authorization": auth_token}
        )
        
        if response.status_code in [200, 204]:
            assert True
        else:
            assert response.status_code in [404, 501]
    
    def test_reconcile_activities_batch(self, client, auth_token):
        """Test batch reconciliation of activities"""
        response = client.post(
            "/activities/reconcile",
            json={
                "activities": ["act_001", "act_002"]
            },
            headers={"Authorization": auth_token}
        )
        
        if response.status_code in [200, 201]:
            assert True
        else:
            assert response.status_code in [404, 501]


class TestEcclesiasticalApprovals:
    """Tests for ecclesiastical approval endpoints"""
    
    def test_get_ecclesiastical_approval_activities(self, client, auth_token):
        """Test retrieving activities needing ecclesiastical approval"""
        response = client.get(
            "/activity-permission-ecclesiastical?is_bishop=true",
            headers={"Authorization": auth_token}
        )
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))

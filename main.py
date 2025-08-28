#!/usr/bin/env python3
"""
Smart iTop Query Processor V2 - Simplified and Class-Specific
"""
import json
import os
import re
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta

import httpx
from fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("itop-mcp")

# Configuration
ITOP_BASE_URL = os.getenv("ITOP_BASE_URL", "")
ITOP_USER = os.getenv("ITOP_USER", "")
ITOP_PASSWORD = os.getenv("ITOP_PASSWORD", "")
ITOP_VERSION = os.getenv("ITOP_VERSION", "1.4")


class ITopClient:
    """Client for interacting with iTop REST API"""
    
    def __init__(self, base_url: str, username: str, password: str, version: str = "1.4"):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.version = version
        self.rest_url = f"{self.base_url}/webservices/rest.php"
    
    async def make_request(self, operation_data: dict) -> dict:
        """Make a REST request to iTop"""
        headers = {
            "User-Agent": "iTop-MCP-Server/1.0",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "version": self.version,
            "auth_user": self.username,
            "auth_pwd": self.password,
            "json_data": json.dumps(operation_data)
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(self.rest_url, data=data, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.RequestError as e:
                raise ConnectionError(f"Request failed: {e}") from e
            except httpx.HTTPStatusError as e:
                raise ValueError(f"HTTP error {e.response.status_code}: {e.response.text}") from e
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON response: {e}") from e

def get_itop_client() -> ITopClient:
    """Get configured iTop client"""
    if not all([ITOP_BASE_URL, ITOP_USER, ITOP_PASSWORD]):
        raise ValueError("Missing required environment variables: ITOP_BASE_URL, ITOP_USER, ITOP_PASSWORD")
    return ITopClient(ITOP_BASE_URL, ITOP_USER, ITOP_PASSWORD, ITOP_VERSION)

ITOP_CLASS_TAXONOMY = {
    "SearchUseCases": [
      {
        "name": "Tickets",
        "classes": ["UserRequest", "Ticket", "Incident", "Problem", "Change"],
        "description": "ITSM ticket objects",
        "keywords": ["user request", "user requests", "support ticket", "support tickets", "show me tickets", "request", "requests", "issue", "issues", "incident", "incidents", "problem", "problems", "known error", "known errors", "root cause", "root cause analysis", "change", "changes", "support"]
      },
      {
        "name": "Change Requests",
        "classes": ["RoutineChange", "NormalChange", "ApprovedChange", "EmergencyChange", "Change"],
        "description": "Various types of change tickets",
        "keywords": ["change request", "change requests", "routine change", "normal change", "approved change", "emergency change", "changes"]
      },
      {
        "name": "PCs / End‑User Devices",
        "classes": ["PC", "PhysicalDevice"],
        "description": "Workstations and user-managed devices",
        "keywords": ["pc", "pcs", "computer", "computers", "desktop", "desktops", "laptop", "laptops", "workstation", "workstations"]
      },
      {
        "name": "Servers & Datacenter Devices",
        "classes": ["Server", "DatacenterDevice", "ConnectableCI"],
        "description": "Physical servers and datacenter assets",
        "keywords": ["server", "servers", "datacenter", "datacenter device", "connectable"]
      },
      {
        "name": "Virtual Machines",
        "classes": ["VirtualMachine", "Hypervisor"],
        "description": "Virtual infrastructure",
        "keywords": ["vm", "vms", "virtual machine", "virtual machines", "hypervisor", "hypervisors", "virtual"]
      },
      {
        "name": "Configuration Items",
        "classes": ["FunctionalCI"],
        "description": "Generic configuration item records",
        "keywords": ["ci", "configuration item", "functionalci"]
      },
      {
        "name": "Network Devices",
        "classes": ["NetworkDevice"],
        "description": "Routers, switches, firewalls, and the like",
        "keywords": ["network device", "router", "switch", "firewall", "network"]
      },
      {
        "name": "Racks, Locations & IPs",
        "classes": ["Rack", "Location", "PhysicalIP", "TapeLibrary"],
        "description": "Infrastructure placement and IP tracking",
        "keywords": ["rack", "location", "physical ip", "ip", "tape library"]
      }
    ],
    "PeopleAndOrganizations": [
      {
        "name": "People & Contacts",
        "classes": ["Person", "Contact"],
        "description": "Individual people and generic contacts",
        "keywords": ["person", "people", "people in organization", "contact", "contacts", "user", "users"]
      },
      {
        "name": "Teams & Organizations",
        "classes": ["Team", "Organization"],
        "description": "Groups or organizational entities",
        "keywords": ["team", "teams", "organization", "organizations", "org", "orgs"]
      }
    ],
    "ApplicationsAndServices": [
      {
        "name": "Applications & Software",
        "classes": ["ApplicationSolution", "SoftwareInstance", "Software", "SoftwarePatch", "Patch", "OSPatch"],
        "description": "Installed software, apps, and patches",
        "keywords": ["application", "applications", "software", "software instance", "patch", "os patch"]
      },
      {
        "name": "Services & SLAs",
        "classes": ["Service", "ServiceFamily", "ServiceSubcategory", "Contract", "ServiceSubcategory", "ServiceFamily", "SLA", "SLT", "CustomerContract", "ProviderContract"],
        "description": "Service entries and service agreements",
        "keywords": ["service", "services", "sla", "slas", "contract", "contracts"]
      }
    ],
    "LinkingClasses": [
      {
        "name": "Linking / Relationship Classes",
        "classes": [
          "lnkContactToTicket", "lnkDocumentToLicence", "lnkSoftwareInstanceToSoftwarePatch",
          "lnkFunctionalCIToTicket", "lnkVirtualDeviceToVolume", "lnkConnectableCIToNetworkDevice"
        ],
        "description": "Association/link tables between records",
        "keywords": ["link", "relationship", "lnk", "assoc", "association"]
      }
    ],
    "OperationalAndAudit": [
      {
        "name": "CMDB Change Logs",
        "classes": ["CMDBChange", "CMDBChangeOp"],
        "description": "Detailed change tracking records",
        "keywords": ["cmdb", "change log", "audit"]
      },
      {
        "name": "Automation / Workflows / Notifications",
        "classes": ["Action", "ActionEmail", "ActionWebhook", "Trigger", "Event"],
        "description": "Workflow actions, triggers, and events",
        "keywords": ["action", "trigger", "workflow", "event", "notification", "webhook"]
      }
    ],
    "SecurityAndUI": [
      {
        "name": "Users & Profiles",
        "classes": ["User", "UserLocal", "UserExternal"],
        "description": "Authentication and user metadata",
        "keywords": ["user", "users", "profile", "profiles", "authentication"]
      }
    ]
}

def smart_class_detection(query: str) -> tuple[str, float, dict]:
    """
    Enhanced class detection with priority handling
    Returns:
        tuple: (best_class_name, confidence_score, query_analysis)
    """
    query_lower = query.lower()
    best_matches = []
    
    # PRIORITY 1: Handle entity + relationship queries (give precedence to main entity)
    # "network devices and their location" should route to NetworkDevice, not Location
    if "network device" in query_lower and "location" in query_lower:
        return "NetworkDevice", 0.95, {"action": "list", "include_relationships": True}
    
    # "software applications installed on server" should route to Server, not Software  
    if ("software" in query_lower or "application" in query_lower) and "server" in query_lower:
        return "Server", 0.95, {"action": "list", "include_relationships": True}
    
    # PRIORITY 2: Distinguish between generic tickets and support tickets
    # Generic "tickets" (without "support") should use Ticket class
    if "tickets" in query_lower and "support" not in query_lower and "user request" not in query_lower:
        return "Ticket", 0.90, {"action": "list", "generic_tickets": True}
    
    # PRIORITY 3: SLA/support ticket queries should use UserRequest  
    sla_patterns = ["sla", "support ticket", "support tickets", "sla issues", "with sla"]
    for pattern in sla_patterns:
        if pattern in query_lower and "change" not in query_lower:
            # Force UserRequest for SLA queries (but not for change requests)
            return "UserRequest", 0.95, {"action": "list", "time_analysis": True}
    
    # PRIORITY 4: Team assignment queries - Use UserRequest for most team-based ticket queries
    if "team" in query_lower and any(ticket_word in query_lower for ticket_word in ["ticket", "tickets", "user request", "support", "assigned"]):
        # Most team-related ticket queries should use UserRequest for better compatibility
        return "UserRequest", 0.90, {"action": "list", "team_filter": True}
    
    # PRIORITY 5: Contact vs Person disambiguation for service managers
    if "contact" in query_lower and "service manager" in query_lower:
        return "Contact", 0.95, {"action": "list", "role_filter": True}
    
    # PRIORITY 6: Standard taxonomy-based detection
    for category_list in ITOP_CLASS_TAXONOMY.values():
        for category in category_list:
            for class_name in category["classes"]:
                score = 0
                
                # Higher score for exact class name matches
                if class_name.lower() in query_lower:
                    score += 60
                
                # Score for keyword matches
                for keyword in category.get("keywords", []):
                    if keyword in query_lower:
                        # Multi-word keywords get higher scores
                        word_count = len(keyword.split())
                        score += word_count * 15
                        
                        # Bonus for exact phrase matches
                        if keyword == query_lower.strip():
                            score += 30
                
                if score > 0:
                    best_matches.append((class_name, score, category))
    
    best_matches.sort(key=lambda x: x[1], reverse=True)
    
    if best_matches:
        best_class, best_score, best_category = best_matches[0]
        
        # Normalize confidence score (0-1)
        confidence = min(best_score / 100.0, 1.0)
        
        return best_class, confidence, {"action": "list", "category": best_category["name"]}
    
    # Default fallback
    return "UserRequest", 0.1, {"action": "list", "fallback": True}

def _extract_count_from_message(message: str) -> int:
    """Extract count from API response message with flexible pattern matching."""
    try:
        if not message:
            return 0
        
        message_lower = message.lower()
        
        # Try multiple flexible patterns in order of preference
        patterns = [
            # iTop common formats
            r'found[:\s]*(\d+)',                    # "Found: 92", "Found 92", "found:92"
            r'(\d+)\s*found',                       # "92 found", "92found"
            r'(\d+)\s*objects?\s*found',            # "92 objects found", "1 object found"
            r'found\s*(\d+)\s*objects?',            # "found 92 objects", "found 1 object"
            r'(\d+)\s*objects?\s*returned',         # "92 objects returned"
            r'returned\s*(\d+)\s*objects?',         # "returned 92 objects"
            r'(\d+)\s*results?',                    # "92 results", "1 result"
            r'results?\s*[:\s]*(\d+)',              # "results: 92", "results 92"
            r'total[:\s]*(\d+)',                    # "total: 92", "total 92"
            r'count[:\s]*(\d+)',                    # "count: 92", "count 92"
            r'(\d+)\s*records?',                    # "92 records", "1 record"
            r'records?\s*[:\s]*(\d+)',              # "records: 92"
            r'(\d+)\s*entries',                     # "92 entries"
            r'entries[:\s]*(\d+)',                  # "entries: 92"
            # Generic number extraction as last resort
            r'(\d+)'                                # Any number in the message
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message_lower)
            if match:
                count = int(match.group(1))
                if 0 <= count <= 1000000:  # Up to 1M records seems reasonable
                    return count
        
        return 0
    except (ValueError, AttributeError):
        return 0

# =============================================================================
# Smart Filter Engine - Universal Filtering Logic
# =============================================================================

class SmartFilterEngine:
    """Universal filter extraction engine that works across all iTop classes"""
    
    # Universal field patterns that work across most iTop classes
    UNIVERSAL_PATTERNS = {
        # Priority patterns (UserRequest, Incident, Problem, etc.)
        "priority": {
            "critical": {"field": "priority", "value": "1", "patterns": ["critical", "priority 1", "p1", "urgent"]},
            "high": {"field": "priority", "value": "2", "patterns": ["high priority", "priority 2", "p2"]},
            "medium": {"field": "priority", "value": "3", "patterns": ["medium priority", "priority 3", "p3"]},
            "low": {"field": "priority", "value": "4", "patterns": ["low priority", "priority 4", "p4"]}
        },
        
        # Status patterns (different for each class but similar concepts)
        "status": {
            "new": {"patterns": ["new", "created", "submitted"]},
            "open": {"patterns": ["open", "ongoing", "active", "in progress"]},
            "closed": {"patterns": ["closed", "completed", "finished"]},
            "resolved": {"patterns": ["resolved", "fixed", "solved"]},
            "pending": {"patterns": ["pending", "waiting", "on hold"]},
            "assigned": {"patterns": ["assigned", "allocated"]},
            "approved": {"patterns": ["approved", "accepted"]},
            "rejected": {"patterns": ["rejected", "denied", "declined"]},
            "implemented": {"patterns": ["implemented", "deployed", "done"]},
            "escalated": {"patterns": ["escalated", "escalation"]}
        },
        
        # Time patterns (universal)
        "time": {
            "today": {"field": "start_date", "operator": ">=", "value_fn": lambda: datetime.now().strftime("%Y-%m-%d 00:00:00")},
            "yesterday": {"field": "start_date", "operator": ">=", "value_fn": lambda: (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")},
            "this_week": {"field": "start_date", "operator": ">=", "value_fn": lambda: (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d 00:00:00")},
            "last_7_days": {"field": "start_date", "operator": ">=", "value_fn": lambda: (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d 00:00:00")},
            "last_15_days": {"field": "start_date", "operator": ">=", "value_fn": lambda: (datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d 00:00:00")},
            "last_30_days": {"field": "start_date", "operator": ">=", "value_fn": lambda: (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d 00:00:00")},
            # FIXED: Use <= for "not updated in X hours" (items older than X hours)
            "24_hours_old": {"field": "last_update", "operator": "<=", "value_fn": lambda: (datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")},
            "48_hours_old": {"field": "last_update", "operator": "<=", "value_fn": lambda: (datetime.now() - timedelta(hours=48)).strftime("%Y-%m-%d %H:%M:%S")}
        },
        
        # Organization/Team patterns
        "organization": {
            "patterns": ["organization", "org", "company"],
            "field": "org_name"
        },
        
        "team": {
            "patterns": ["team", "group", "department"],
            "field": "team_name"
        },
        
        # People patterns
        "caller": {
            "patterns": ["caller", "user", "requester"],
            "field": "caller_name"
        },
        
        "agent": {
            "patterns": ["agent", "assignee", "assigned to"],
            "field": "agent_name"
        }
    }
    
    # Class-specific field mappings
    CLASS_FIELD_MAPPINGS = {
        "UserRequest": {
            "status_field": "status",
            "status_values": {
                "new": "new", "open": ["new", "assigned", "pending"], "closed": "closed",
                "resolved": "resolved", "pending": "pending", "assigned": "assigned"
            }
        },
        "Ticket": {
            "status_field": "operational_status", 
            "status_values": {
                "open": "ongoing", "closed": "closed", "resolved": "resolved"
            }
        },
        "Change": {
            "status_field": "status",
            "status_values": {
                "new": "new", "approved": "approved", "implemented": "implemented",
                "closed": "closed", "rejected": "rejected", "completed": ["implemented", "closed"],
                "open": ["new", "approved"], "not_completed": ["new", "approved", "rejected"]
            }
        },
        "Incident": {
            "status_field": "status",
            "status_values": {
                "new": "new", "assigned": "assigned", "resolved": "resolved", 
                "closed": "closed", "pending": "pending"
            }
        },
        "Problem": {
            "status_field": "status",
            "status_values": {
                "new": "new", "assigned": "assigned", "resolved": "resolved",
                "closed": "closed", "known_error": "known_error"
            }
        }
    }
    
    @classmethod
    def extract_filters(cls, query_lower: str, class_name: str) -> List[Dict[str, Any]]:
        """Smart filter extraction that adapts to different iTop classes"""
        filters = []
        
        # Extract priority filters (universal)
        # Only for classes that support priority field (not generic Ticket class)
        if class_name not in ["Ticket"]:
            priority_filter = cls._extract_priority_filter(query_lower)
            if priority_filter:
                filters.append(priority_filter)
        
        # Extract status filters (class-specific)
        status_filter = cls._extract_status_filter(query_lower, class_name)
        if status_filter:
            filters.append(status_filter)
        
        # Extract time filters (universal)
        time_filter = cls._extract_time_filter(query_lower)
        if time_filter:
            filters.append(time_filter)
        
        # Extract organization/team filters
        org_filter = cls._extract_organization_filter(query_lower)
        if org_filter:
            filters.append(org_filter)
        
        # Extract class-specific filters
        class_filters = cls._extract_class_specific_filters(query_lower, class_name)
        filters.extend(class_filters)
        
        return filters
    
    @classmethod
    def _extract_priority_filter(cls, query_lower: str) -> Optional[Dict[str, Any]]:
        """Extract priority filters dynamically - works for most ticket classes but NOT for generic Ticket class"""
        # Don't use priority field for generic Ticket class as it doesn't have it
        # Priority is available in subclasses like UserRequest, Incident, Problem
        
        # Dynamic priority mapping - can be extended easily
        priority_mappings = {
            "critical": "1", "priority 1": "1", "p1": "1", "urgent": "1",
            "high": "2", "priority 2": "2", "p2": "2", "high priority": "2",
            "medium": "3", "priority 3": "3", "p3": "3", "normal": "3", "medium priority": "3",
            "low": "4", "priority 4": "4", "p4": "4", "low priority": "4"
        }
        
        # Find all priority terms mentioned in the query
        found_priorities = []
        for priority_term, priority_value in priority_mappings.items():
            if priority_term in query_lower:
                found_priorities.append((priority_term, priority_value))
        
        if not found_priorities:
            return None
        
        if len(found_priorities) == 1:
            # Single priority
            term, value = found_priorities[0]
            return {
                "field": "priority",
                "operator": "=",
                "value": value,
                "display_name": f"{term} priority"
            }
        else:
            # Multiple priorities - use IN operator for OR logic
            unique_values = list(set([value for _, value in found_priorities]))
            unique_terms = list(set([term for term, _ in found_priorities]))
            
            if len(unique_values) == 1:
                # Multiple terms mapping to same priority value
                return {
                    "field": "priority", 
                    "operator": "=",
                    "value": unique_values[0],
                    "display_name": f"{'/'.join(unique_terms)} priority"
                }
            else:
                # Multiple different priorities
                return {
                    "field": "priority",
                    "operator": "IN", 
                    "values": unique_values,
                    "display_name": f"{'/'.join(unique_terms)} priority"
                }
    
    @classmethod
    def _extract_status_filter(cls, query_lower: str, class_name: str) -> Optional[Dict[str, Any]]:
        """Extract status filters - only when explicitly mentioned as filters"""
        class_mapping = cls.CLASS_FIELD_MAPPINGS.get(class_name, {})
        status_field = class_mapping.get("status_field", "status")
        status_values = class_mapping.get("status_values", {})
        
        # Only add status filters when they appear to be intentional filters
        # Look for patterns like "closed tickets", "open requests", etc.
        status_filter_patterns = {
            "new": [r'\bnew\s+(?:tickets|requests|incidents|changes|problems)\b'],
            "open": [r'\bopen\s+(?:tickets|requests|incidents|changes|problems)\b', r'\bongoing\s+(?:tickets|requests|incidents|changes|problems)\b'],
            "closed": [r'\bclosed\s+(?:tickets|requests|incidents|changes|problems)\b'],
            "resolved": [r'\bresolved\s+(?:tickets|requests|incidents|changes|problems)\b'],
            "pending": [r'\bpending\s+(?:tickets|requests|incidents|changes|problems)\b'],
            "assigned": [r'\bassigned\s+(?:tickets|requests|incidents|changes|problems)\b']
        }
        
        for status_concept, patterns in status_filter_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    # Map to class-specific status value
                    class_status_value = status_values.get(status_concept)
                    if class_status_value:
                        if isinstance(class_status_value, list):
                            return {
                                "field": status_field,
                                "operator": "IN",
                                "values": class_status_value,
                                "display_name": f"{status_concept} status"
                            }
                        else:
                            return {
                                "field": status_field,
                                "operator": "=",
                                "value": class_status_value,
                                "display_name": f"{status_concept} status"
                            }
        return None
    
    @classmethod
    def _extract_time_filter(cls, query_lower: str) -> Optional[Dict[str, Any]]:
        """Extract time-based filters"""
        # Enhanced patterns for time-based queries
        time_patterns = {
            "today": ["today"],
            "yesterday": ["yesterday"],
            "this_week": ["this week", "past week"],
            "last_7_days": ["last 7 days", "7 days", "past 7 days"],
            "last_15_days": ["last 15 days", "15 days", "past 15 days"],
            "last_30_days": ["last 30 days", "30 days", "past 30 days"],
            "24_hours_old": ["24 hours", "not updated in 24 hours", "not updated in the last 24 hours"],
            "48_hours_old": ["48 hours", "not updated in 48 hours", "not updated in the last 48 hours"]
        }
        
        for time_key, patterns in time_patterns.items():
            for pattern in patterns:
                if pattern in query_lower:
                    time_config = cls.UNIVERSAL_PATTERNS["time"][time_key]
                    return {
                        "field": time_config["field"],
                        "operator": time_config["operator"],
                        "value": time_config["value_fn"](),
                        "display_name": pattern
                    }
        
        # Handle more flexible time patterns with regex
        # Pattern: "not updated in the last X hours"
        hours_match = re.search(r'not updated in (?:the last )?(\d+) hours?', query_lower)
        if hours_match:
            hours = int(hours_match.group(1))
            cutoff_time = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
            return {
                "field": "last_update",
                "operator": "<=",
                "value": cutoff_time,
                "display_name": f"not updated in the last {hours} hours"
            }
        
        return None
    
    @classmethod
    def _extract_organization_filter(cls, query_lower: str) -> Optional[Dict[str, Any]]:
        """Extract organization/team filters"""
        # Look for specific organization mentions
        org_match = re.search(r'organization ["\']([^"\']+)["\']|org ["\']([^"\']+)["\']', query_lower)
        if org_match:
            org_name = org_match.group(1) or org_match.group(2)
            return {
                "field": "org_name",
                "operator": "LIKE",
                "value": f"%{org_name}%",
                "display_name": f"organization contains '{org_name}'"
            }
        
        # Look for team mentions
        team_match = re.search(r'team ["\']([^"\']+)["\']', query_lower)
        if team_match:
            team_name = team_match.group(1)
            return {
                "field": "team_name",
                "operator": "LIKE",
                "value": f"%{team_name}%",
                "display_name": f"team contains '{team_name}'"
            }
        
        return None
    
    @classmethod
    def _extract_class_specific_filters(cls, query_lower: str, class_name: str) -> List[Dict[str, Any]]:
        """Extract filters specific to the class"""
        filters = []
        
        # Enhanced team assignment filters for ticket classes
        if class_name in ["Ticket", "UserRequest", "Incident", "Problem", "Change"]:
            # More precise team matching patterns
            team_patterns = [
                (r'assigned to (?:the )?(\w+(?:\s+\w+){0,2})(?:\s+team|\s*$)', 1),           # "assigned to support team"
                (r'team ["\']([^"\']+)["\']', 1),                                           # 'team "support"'
                (r'(\w+(?:\s+\w+){0,1})\s+team(?:\s|$)', 1),                             # "support team", "database team"
                (r'tickets?\s+(?:for|from|by)\s+(?:the\s+)?(\w+(?:\s+\w+){0,2})\s+team', 1),  # "tickets for support team"
                (r'(?:for|by)\s+(\w+(?:\s+\w+){0,1})(?:\s+team|\s*$)', 1)                # "for support", "by infrastructure"
            ]
            
            for pattern, group_idx in team_patterns:
                team_match = re.search(pattern, query_lower)
                if team_match:
                    team_name = team_match.group(group_idx).strip()
                    # Filter out common words and ensure it's a reasonable team name
                    excluded_words = {'the', 'and', 'for', 'by', 'to', 'in', 'on', 'with', 'from', 'tickets', 'ticket', 'user', 'requests', 'request', 'incidents', 'incident', 'show', 'me'}
                    if len(team_name) > 2 and team_name not in excluded_words and not any(word in excluded_words for word in team_name.split()):
                        filters.append({
                            "field": "team_name",
                            "operator": "LIKE",
                            "value": f"%{team_name}%",
                            "display_name": f"team: {team_name}"
                        })
                        break  # Only add one team filter to avoid duplicates
        
        # Simplified SLA filters for classes that support it (only add if explicitly mentioned)
        if class_name in ["UserRequest", "Incident"]:
            # Only add SLA filters for explicit SLA-related queries to avoid over-filtering
            if "sla breach" in query_lower or "sla missed" in query_lower:
                filters.append({
                    "field": "sla_ttr_passed",
                    "operator": "=",
                    "value": "yes",  # "yes" means SLA was passed/missed (late)
                    "display_name": "SLA breached"
                })
            elif "sla met" in query_lower:
                filters.append({
                    "field": "sla_ttr_passed", 
                    "operator": "=",
                    "value": "no",  # "no" means SLA was not passed/missed (on time)
                    "display_name": "SLA met"
                })
        
        # Change-specific filters (only for actual Change class)
        if class_name == "Change":
            if "emergency" in query_lower:
                filters.append({
                    "field": "finalclass",
                    "operator": "=",
                    "value": "EmergencyChange",
                    "display_name": "emergency changes"
                })
            elif "normal" in query_lower and "change" in query_lower:
                filters.append({
                    "field": "finalclass",
                    "operator": "=",
                    "value": "NormalChange",
                    "display_name": "normal changes"
                })
            elif "routine" in query_lower:
                filters.append({
                    "field": "finalclass",
                    "operator": "=",
                    "value": "RoutineChange",
                    "display_name": "routine changes"
                })
        
        return filters

# =============================================================================
# Smart Query Builder - Universal OQL Generation
# =============================================================================

class SmartQueryBuilder:
    """Universal OQL query builder that works across all iTop classes"""
    
    @classmethod
    def build_oql_query(cls, class_name: str, filters: List[Dict[str, Any]]) -> str:
        """Build OQL query from filters"""
        base_query = f"SELECT {class_name}"
        conditions = []
        
        # Group filters by field to avoid duplicates
        field_filters = {}
        for filter_info in filters:
            field = filter_info["field"]
            if field not in field_filters:
                field_filters[field] = []
            field_filters[field].append(filter_info)
        
        # Build conditions, combining multiple filters for the same field
        for field, filter_list in field_filters.items():
            if len(filter_list) == 1:
                # Single filter for this field
                condition = cls._build_condition(filter_list[0])
                if condition:
                    conditions.append(condition)
            else:
                # Multiple filters for same field - combine with OR if they're IN operators
                in_values = []
                other_conditions = []
                
                for filter_info in filter_list:
                    if filter_info["operator"] == "IN":
                        in_values.extend(filter_info.get("values", []))
                    else:
                        condition = cls._build_condition(filter_info)
                        if condition:
                            other_conditions.append(condition)
                
                if in_values:
                    # Deduplicate values
                    unique_values = list(set(in_values))
                    if len(unique_values) == 1:
                        conditions.append(f"{field} = '{unique_values[0]}'")
                    else:
                        values_str = "', '".join(unique_values)
                        conditions.append(f"{field} IN ('{values_str}')")
                
                conditions.extend(other_conditions)
        
        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)
        
        return base_query
    
    @classmethod
    def _build_condition(cls, filter_info: Dict[str, Any]) -> str:
        """Build a single OQL condition from filter info"""
        field = filter_info["field"]
        operator = filter_info["operator"]
        
        if operator == "IN":
            values = filter_info["values"]
            values_str = "', '".join(values)
            return f"{field} IN ('{values_str}')"
        elif operator == "LIKE":
            value = filter_info["value"]
            return f"{field} LIKE '{value}'"
        elif operator in ["=", "!=", ">", "<", ">=", "<="]:
            value = filter_info["value"]
            return f"{field} {operator} '{value}'"
        
        return ""

# =============================================================================
# Smart Grouping Engine - Universal Grouping Logic
# =============================================================================

class SmartGroupingEngine:
    """Universal grouping logic that works across all iTop classes"""
    
    # Universal grouping field mappings
    GROUPING_MAPPINGS = {
        "status": {"UserRequest": "status", "Ticket": "operational_status", "Change": "status", "Incident": "status", "Problem": "status"},
        "priority": "priority",  # Universal field
        "organization": "org_name",  # Universal field
        "team": "team_name",  # Universal field
        "agent": "agent_name",  # Universal field
        "type": "finalclass",  # Universal field for class identification
        "caller": "caller_name"  # Universal field
    }
    
    @classmethod
    def detect_grouping(cls, query_lower: str, class_name: str) -> Optional[str]:
        """Detect what field to group by from the query"""
        grouping_patterns = {
            "status": ["by status", "group by status", "status wise", "breakdown by status"],
            "priority": ["by priority", "group by priority", "priority wise", "breakdown by priority"],
            "organization": ["by organization", "by org", "organization wise", "org wise", "group by organization"],
            "team": ["by team", "group by team", "team wise", "breakdown by team"],
            "agent": ["by agent", "group by agent", "agent wise", "breakdown by agent"],
            "type": ["by type", "group by type", "type wise", "breakdown by type"],
            "caller": ["by caller", "group by caller", "caller wise", "breakdown by caller"]
        }
        
        for group_concept, patterns in grouping_patterns.items():
            for pattern in patterns:
                if pattern in query_lower:
                    # Map to actual field name for this class
                    field_mapping = cls.GROUPING_MAPPINGS.get(group_concept)
                    if isinstance(field_mapping, dict):
                        return field_mapping.get(class_name, group_concept)
                    else:
                        return field_mapping
        
        return None
    
    @classmethod
    def format_grouped_results(cls, objects: dict, group_field: str, class_name: str) -> str:
        """Enhanced grouped results formatter that shows details, not just counts"""
        if not objects:
            return f"**No data to group by {group_field}**\n"
        
        groups = {}
        group_details = {}
        
        for obj_key, obj_data in objects.items():
            if obj_data.get("code") == 0:
                fields = obj_data.get("fields", {})
                group_value = fields.get(group_field, "Unknown")
                
                if group_value not in groups:
                    groups[group_value] = 0
                    group_details[group_value] = []
                
                groups[group_value] += 1
                group_details[group_value].append((obj_key, fields))
        
        output = f"**{class_name} Grouped by {group_field.replace('_', ' ').title()}:**\n\n"
        
        for group_name in sorted(groups.keys()):
            count = groups[group_name]
            details = group_details[group_name]
            
            output += f"## **{group_name}** ({count} items)\n"
            
            # Show first few items with details (limit to avoid overwhelming)
            shown_items = min(5, len(details))
            for i, (obj_key, fields) in enumerate(details[:shown_items], 1):
                # Get meaningful identifier
                identifier = (fields.get("ref") or 
                            fields.get("name") or 
                            fields.get("friendlyname") or 
                            fields.get("title") or 
                            obj_key)
                
                # Get status or description
                status_info = ""
                if fields.get("operational_status"):
                    status_info = f" (Status: {fields['operational_status']})"
                elif fields.get("status"):
                    status_info = f" (Status: {fields['status']})"
                
                # Get additional context
                context = ""
                if fields.get("caller_name"):
                    context += f" - Caller: {fields['caller_name']}"
                elif fields.get("team_name"):
                    context += f" - Team: {fields['team_name']}"
                
                output += f"{i}. **{identifier}**{status_info}{context}\n"
            
            if len(details) > shown_items:
                remaining = len(details) - shown_items
                output += f"   ... and {remaining} more items\n"
            
            output += "\n"
        
        return output

# =============================================================================
# Universal Smart Handler Base Class
# =============================================================================

class SmartHandlerBase:
    """Universal base handler that all specific handlers inherit from"""
    
    def __init__(self, client: ITopClient, class_name: str):
        self.client = client
        self.class_name = class_name
    
    def parse_query_intent(self, query: str) -> Dict[str, Any]:
        """Universal query intent parser"""
        query_lower = query.lower()
        
        intent = {
            "action": "list",
            "filters": [],
            "grouping": None,
            "comparison": False,
            "sla_analysis": False
        }
        
        # Detect action type - Enhanced comparison detection first with high priority
        is_comparison = any(word in query_lower for word in ["vs", "versus", "v/s", "compared to"])
        is_count_request = any(word in query_lower for word in ["count", "how many", "total"]) and not is_comparison
        is_grouping = any(word in query_lower for word in ["group by", "grouped by", "breakdown", "summary", "organization wise", "org wise", "by organization", "by org", "by status", "by priority", "by team", "by agent", "by type"]) and not is_comparison
        
        # PRIORITY ORDER: comparison > count > grouping > list
        # This ensures that queries like "grouped by X: A vs B" are treated as comparisons
        if is_comparison:
            intent["action"] = "compare"
            intent["comparison"] = True
        elif is_count_request:
            intent["action"] = "count"
        elif is_grouping:
            intent["action"] = "group"
        
        # Enhanced SLA comparison detection - ONLY for explicit SLA mentions
        # Only apply SLA comparison when both "sla" AND comparison terms are present
        sla_comparison_patterns = [
            r"sla.*closed on time.*not closed on time",  # SLA with explicit timing language
            r"sla.*closed vs not closed",                # SLA mentioned with closed comparison
            r"closed vs not closed.*sla",                # Closed comparison with SLA mentioned
            r"sla.*on time vs not on time",              # SLA with timing comparison
            r"on time vs not on time.*sla",              # Timing comparison with SLA
            r"met sla vs missed sla",                    # Direct SLA comparison
            r"sla met vs sla missed",                    # Direct SLA comparison
            r"support tickets closed on time vs not closed on time based on sla",
            r"closed vs not closed on time.*sla", 
            r"closed vs not closed.*on time.*sla",
            r".*closed on time.*not closed on time.*based on sla.*",  # More flexible pattern
            r".*sla.*closed on time.*not closed on time.*"   # More flexible pattern
        ]
        
        # Check if this is an SLA-related comparison (must have explicit SLA mention)
        is_sla_comparison = False
        if "sla" in query_lower:  # Only check patterns if SLA is mentioned
            for pattern in sla_comparison_patterns:
                if re.search(pattern, query_lower, re.IGNORECASE):
                    is_sla_comparison = True
                    intent["action"] = "compare"
                    intent["comparison"] = True
                    intent["sla_analysis"] = True
                    break
        
        # Detect SLA analysis
        if any(word in query_lower for word in ["sla"]):
            intent["sla_analysis"] = True
        
        # Extract filters using smart engine
        intent["filters"] = SmartFilterEngine.extract_filters(query_lower, self.class_name)
        
        # Extract grouping using smart engine
        intent["grouping"] = SmartGroupingEngine.detect_grouping(query_lower, self.class_name)
        
        return intent
    
    def build_oql_query(self, intent: Dict[str, Any]) -> str:
        """Build OQL query using smart query builder"""
        return SmartQueryBuilder.build_oql_query(self.class_name, intent["filters"])
    
    def determine_output_fields(self, intent: Dict[str, Any]) -> str:
        """Universal output field determination"""
        if intent["action"] == "count":
            if intent["grouping"]:
                return f"id,{intent['grouping']}"
            else:
                return "id"
        
        # For detailed queries, use all fields
        return "*+"
    
    async def process_query(self, query: str, limit: int = 100) -> str:
        """Universal query processor"""
        try:
            intent = self.parse_query_intent(query)
            
            # Handle comparison queries
            if intent["comparison"]:
                return await self._handle_comparison_query(query, intent, limit)
            
            # Build and execute query
            oql_query = self.build_oql_query(intent)
            output_fields = self.determine_output_fields(intent)
            
            operation = {
                "operation": "core/get",
                "class": self.class_name,
                "key": oql_query,
                "output_fields": output_fields,
                "limit": limit
            }
            
            result = await self.client.make_request(operation)
            
            # Check for errors
            if result.get("code") != 0:
                error_msg = result.get("message", "Unknown error")
                if "unknown class" in error_msg.lower() or "class not found" in error_msg.lower():
                    return f"⚠️ **{self.class_name} Class Not Available**: The {self.class_name} class may not be configured in your iTop instance.\n\n**Error**: {error_msg}\n\n**Suggestion**: Use the generic Ticket handler instead or contact your iTop administrator."
                return f"❌ **{self.class_name} Query Error**: {error_msg}"
            
            return self._format_results(result, intent, query, oql_query)
            
        except Exception as e:
            return f"❌ **{self.class_name} Handler Error**: {str(e)}"
    
    async def _handle_comparison_query(self, query: str, intent: Dict[str, Any], limit: int) -> str:
        """Universal comparison query handler"""
        query_lower = query.lower()
        
        # Enhanced SLA comparison detection - ONLY when SLA is explicitly mentioned
        sla_patterns = [
            r"sla.*closed on time.*not closed on time",  # SLA with explicit timing language
            r"sla.*closed vs not closed",                # SLA mentioned with closed comparison
            r"closed vs not closed.*sla",                # Closed comparison with SLA mentioned
            r"sla.*on time vs not on time",              # SLA with timing comparison
            r"on time vs not on time.*sla",              # Timing comparison with SLA
            r"met sla vs missed sla",                    # Direct SLA comparison
            r"sla met vs sla missed",                    # Direct SLA comparison
            r"support tickets closed on time vs not closed on time based on sla",
            r"closed vs not closed on time.*sla", 
            r"closed vs not closed.*on time.*sla",
            r".*closed on time.*not closed on time.*based on sla.*",  # More flexible pattern
            r".*sla.*closed on time.*not closed on time.*"   # More flexible pattern
        ]
        
        # Check if this is an SLA-related comparison (SLA must be explicitly mentioned)
        # BUT only apply SLA logic for UserRequest/Incident classes, not generic Ticket
        is_sla_comparison = False
        if "sla" in query_lower and self.class_name in ["UserRequest", "Incident"]:  
            is_sla_comparison = any(re.search(pattern, query_lower, re.IGNORECASE) for pattern in sla_patterns)
        
        # Apply SLA comparison only if SLA is explicitly mentioned AND class supports it
        if is_sla_comparison:
            return await self._handle_sla_comparison(query, intent, limit)
        
        # Handle "closed vs not closed" or "completed vs not completed" comparisons
        if ("closed" in query_lower and "not closed" in query_lower) or ("completed" in query_lower and "not completed" in query_lower):
            return await self._handle_closed_vs_open_comparison(query, intent, limit)
        
        # Extract comparison terms
        comparison_match = re.search(r'(\w+)\s+(vs|versus|v/s|compared to)\s+(\w+)', query_lower)
        if not comparison_match:
            return "❌ Could not parse comparison query"
        
        term1, _, term2 = comparison_match.groups()
        
        results = {}
        oqls = {}
        
        # Get class-specific status field
        class_mapping = SmartFilterEngine.CLASS_FIELD_MAPPINGS.get(self.class_name, {})
        status_field = class_mapping.get("status_field", "status")
        status_values = class_mapping.get("status_values", {})
        
        # Execute query for each term
        for term in [term1, term2]:
            term_intent = intent.copy()
            term_intent["filters"] = []
            
            # Map term to class-specific status values
            if term in status_values:
                class_status_value = status_values[term]
                if isinstance(class_status_value, list):
                    term_intent["filters"].append({
                        "field": status_field,
                        "operator": "IN",
                        "values": class_status_value,
                        "display_name": term
                    })
                else:
                    term_intent["filters"].append({
                        "field": status_field,
                        "operator": "=",
                        "value": class_status_value,
                        "display_name": term
                    })
            
            oql_query = self.build_oql_query(term_intent)
            oqls[term] = oql_query
            
            operation = {
                "operation": "core/get",
                "class": self.class_name,
                "key": oql_query,
                "output_fields": f"id,{status_field}",
                "limit": limit
            }
            
            result = await self.client.make_request(operation)
            
            if result.get("code") == 0:
                count = _extract_count_from_message(result.get("message", ""))
                if count is None:
                    count = len(result.get("objects", {}))
                results[term] = count
            else:
                results[term] = f"Error: {result.get('message')}"
        
        # Format results
        output = f"**🔄 {self.class_name} Comparison: {term1.title()} vs {term2.title()}**\n\n"
        output += f"**Query**: \"{query}\"\n\n"
        
        for term in [term1, term2]:
            output += f"**OQL for {term.title()}**: `{oqls[term]}`\n"
        output += "\n"
        
        for term, count in results.items():
            if isinstance(count, int):
                output += f"📊 **{term.title()}**: {count} {self.class_name.lower()}s\n"
            else:
                output += f"❌ **{term.title()}**: {count}\n"
        
        return output
    
    async def _handle_closed_vs_open_comparison(self, query: str, intent: Dict[str, Any], limit: int) -> str:
        """Handle closed vs open/not closed comparisons - always show both counts"""
        
        # Get class-specific status field
        class_mapping = SmartFilterEngine.CLASS_FIELD_MAPPINGS.get(self.class_name, {})
        status_field = class_mapping.get("status_field", "status")
        status_values = class_mapping.get("status_values", {})
        
        results = {}
        oqls = {}
        
        # Handle Change requests "completed vs not completed" 
        if self.class_name == "Change" and ("completed" in query.lower() or "complete" in query.lower()):
            # Query 1: Completed changes (implemented or closed)
            completed_intent = intent.copy()
            completed_values = status_values.get("completed", ["implemented", "closed"])
            completed_intent["filters"] = [
                {
                    "field": status_field,
                    "operator": "IN",
                    "values": completed_values,
                    "display_name": "completed"
                }
            ]
            
            # Query 2: Not completed changes (new, approved, rejected)
            not_completed_intent = intent.copy()
            not_completed_values = status_values.get("not_completed", ["new", "approved", "rejected"])
            not_completed_intent["filters"] = [
                {
                    "field": status_field,
                    "operator": "IN", 
                    "values": not_completed_values,
                    "display_name": "not completed"
                }
            ]
            
            comparisons = [
                ("completed", completed_intent),
                ("not_completed", not_completed_intent)
            ]
        else:
            # Standard closed vs open comparison
            # Query 1: Closed items
            closed_intent = intent.copy()
            closed_intent["filters"] = [
                {
                    "field": status_field,
                    "operator": "=",
                    "value": "closed",
                    "display_name": "closed"
                }
            ]
            
            # Query 2: Open/ongoing items (not closed)
            open_intent = intent.copy()
            if self.class_name == "Ticket":
                open_intent["filters"] = [
                    {
                        "field": status_field,
                        "operator": "=",
                        "value": "ongoing",
                        "display_name": "ongoing/open"
                    }
                ]
            else:
                # For other classes, use a more generic approach
                open_intent["filters"] = [
                    {
                        "field": status_field,
                        "operator": "!=",
                        "value": "closed",
                        "display_name": "not closed"
                    }
                ]
            
            comparisons = [
                ("closed", closed_intent),
                ("open", open_intent)
            ]
        
        for term, term_intent in comparisons:
            oql_query = self.build_oql_query(term_intent)
            oqls[term] = oql_query
            
            operation = {
                "operation": "core/get",
                "class": self.class_name,
                "key": oql_query,
                "output_fields": f"id,{status_field}",
                "limit": limit
            }
            
            result = await self.client.make_request(operation)
            
            if result.get("code") == 0:
                count = _extract_count_from_message(result.get("message", ""))
                if count is None:
                    count = len(result.get("objects", {}))
                results[term] = count
            else:
                results[term] = f"Error: {result.get('message')}"
        
        # Format results - always show both counts
        if self.class_name == "Change" and ("completed" in query.lower() or "complete" in query.lower()):
            output = f"**🔄 {self.class_name} Completion Comparison**\n\n"
            output += f"**Query**: \"{query}\"\n\n"
            
            output += f"**OQL for Completed**: `{oqls.get('completed', 'N/A')}`\n"
            output += f"**OQL for Not Completed**: `{oqls.get('not_completed', 'N/A')}`\n\n"
            
            completed_count = results.get('completed', 0)
            not_completed_count = results.get('not_completed', 0)
            
            output += f"📊 **Completed**: {completed_count} {self.class_name.lower()}s\n"
            output += f"📊 **Not Completed**: {not_completed_count} {self.class_name.lower()}s\n"
        else:
            output = f"**🔄 {self.class_name} Status Comparison**\n\n"
            output += f"**Query**: \"{query}\"\n\n"
            
            output += f"**OQL for Closed**: `{oqls.get('closed', 'N/A')}`\n"
            output += f"**OQL for Open**: `{oqls.get('open', 'N/A')}`\n\n"
            
            closed_count = results.get('closed', 0)
            open_count = results.get('open', 0)
            
            output += f"📊 **Closed**: {closed_count} {self.class_name.lower()}s\n"
            output += f"📊 **Open/Ongoing**: {open_count} {self.class_name.lower()}s\n"
        
        # Calculate total for both cases
        all_counts = [v for v in results.values() if isinstance(v, int)]
        total = sum(all_counts)
        if total > 0:
            output += f"📊 **Total**: {total} {self.class_name.lower()}s\n"
        
        return output
    
    async def _handle_sla_comparison(self, query: str, intent: Dict[str, Any], limit: int) -> str:
        """Universal SLA comparison handler"""
        if self.class_name not in ["UserRequest", "Incident"]:
            return f"❌ SLA comparison not supported for {self.class_name}"
        
        results = {}
        oqls = {}
        
        # Query 1: Closed on time (status=closed AND sla_ttr_passed=no) - CORRECTED LOGIC
        # sla_ttr_passed="no" means SLA was NOT passed/missed, i.e., closed on time
        closed_on_time_intent = intent.copy()
        closed_on_time_intent["filters"] = [
            {
                "field": "status",
                "operator": "=",
                "value": "closed",
                "display_name": "closed"
            },
            {
                "field": "sla_ttr_passed",
                "operator": "=",
                "value": "no",
                "display_name": "SLA not missed (closed on time)"
            }
        ]
        
        # Query 2: Not closed on time (sla_ttr_passed=yes) - CORRECTED LOGIC  
        # sla_ttr_passed="yes" means SLA was passed/missed, i.e., closed late
        not_closed_on_time_intent = intent.copy()
        not_closed_on_time_intent["filters"] = [
            {
                "field": "sla_ttr_passed",
                "operator": "=",
                "value": "yes",
                "display_name": "SLA missed (closed late)"
            }
        ]
        
        comparisons = [
            ("closed_on_time", closed_on_time_intent),
            ("not_closed_on_time", not_closed_on_time_intent)
        ]
        
        for term, term_intent in comparisons:
            oql_query = self.build_oql_query(term_intent)
            oqls[term] = oql_query
            
            operation = {
                "operation": "core/get",
                "class": self.class_name,
                "key": oql_query,
                "output_fields": "id,status,sla_ttr_passed",
                "limit": limit
            }
            
            result = await self.client.make_request(operation)
            
            if result.get("code") == 0:
                count = _extract_count_from_message(result.get("message", ""))
                if count is None:
                    count = len(result.get("objects", {}))
                results[term] = count
            else:
                results[term] = f"Error: {result.get('message')}"
        
        # Format results
        output = f"**🔄 {self.class_name} SLA Comparison: Closed On Time vs Not Closed On Time**\n\n"
        output += f"**Query**: \"{query}\"\n\n"
        
        output += f"**OQL for Closed On Time**: `{oqls['closed_on_time']}`\n"
        output += f"**OQL for Not Closed On Time**: `{oqls['not_closed_on_time']}`\n\n"
        
        closed_count = results.get('closed_on_time', 0)
        not_closed_count = results.get('not_closed_on_time', 0)
        
        output += f"📊 **Closed On Time**: {closed_count} {self.class_name.lower()}s\n"
        output += f"📊 **Not Closed On Time**: {not_closed_count} {self.class_name.lower()}s\n"
        
        return output
    
    def _format_results(self, result: dict, intent: Dict[str, Any], query: str, oql_query: str) -> str:
        """Universal results formatter"""
        if result.get("code") != 0:
            return f"❌ **{self.class_name} Query Error**: {result.get('message', 'Unknown error')}"
        
        objects = result.get("objects", {})
        message = result.get("message", "")
        total_count = _extract_count_from_message(message)
        
        # Get appropriate emoji for class
        emoji_map = {
            "UserRequest": "🎫",
            "Ticket": "🎫", 
            "Change": "🔄",
            "Incident": "🚨",
            "Problem": "🔍"
        }
        emoji = emoji_map.get(self.class_name, "📋")
        
        output = f"**{emoji} {self.class_name} Query Results**\n\n"
        output += f"**Query**: \"{query}\"\n"
        output += f"**OQL Used**: `{oql_query}`\n"
        
        if intent["filters"]:
            filter_descriptions = [f.get("display_name", "unknown filter") for f in intent["filters"] if f and isinstance(f, dict)]
            if filter_descriptions:
                output += f"**Filters Applied**: {', '.join(filter_descriptions)}\n"
        
        if total_count is not None:
            output += f"**Total Found**: {total_count}\n"
        output += f"**Returned**: {len(objects) if objects else 0}\n\n"
        
        if not objects:
            return output + f"No {self.class_name.lower()}s found matching your criteria."
        
        if intent["action"] == "count":
            return output + f"**Total {self.class_name}s**: {total_count or (len(objects) if objects else 0)}"
        elif intent["action"] == "group":
            return output + SmartGroupingEngine.format_grouped_results(objects, intent["grouping"], self.class_name)
        else:
            return output + self._format_detailed_results(objects, intent)
    
    def _format_detailed_results(self, objects: dict, intent: Dict[str, Any]) -> str:
        """Universal detailed results formatter"""
        output = ""
        
        # Group by type if it's a generic Ticket query
        if self.class_name == "Ticket":
            type_groups = {}
            for obj_key, obj_data in objects.items():
                if obj_data.get("code") == 0:
                    fields = obj_data.get("fields", {})
                    ticket_type = fields.get("finalclass", "Unknown")
                    if ticket_type not in type_groups:
                        type_groups[ticket_type] = []
                    type_groups[ticket_type].append((obj_key, obj_data))
            
            for ticket_type, tickets in type_groups.items():
                if tickets:
                    output += f"### {ticket_type} ({len(tickets)})\n"
                    output += self._format_ticket_group(tickets)
                    output += "\n"
        else:
            # Single class formatting
            for i, (obj_key, obj_data) in enumerate(objects.items(), 1):
                if obj_data.get("code") == 0:
                    output += self._format_single_record(i, obj_key, obj_data, intent)
        
        return output
    
    def _format_ticket_group(self, tickets: list) -> str:
        """Format a group of tickets"""
        output = ""
        for i, (obj_key, obj_data) in enumerate(tickets, 1):
            output += self._format_single_record(i, obj_key, obj_data, {})
        return output
    
    def _format_single_record(self, index: int, obj_key: str, obj_data: dict, intent: Dict[str, Any]) -> str:
        """Format a single record universally"""
        fields = obj_data.get("fields", {})
        
        # Get key identifiers
        ref = fields.get("ref", obj_key)
        title = fields.get("title", fields.get("name", fields.get("friendlyname", "No title")))
        
        # Get status (adapt to class)
        status = fields.get("status", fields.get("operational_status", "Unknown"))
        
        output = f"{index}. **{ref}** - {title}\n"
        output += f"   Status: {status}"
        
        # Add priority if available
        if fields.get("priority"):
            priority_emoji = {"1": "🔴", "2": "🟡", "3": "🟢", "4": "⚪"}.get(str(fields["priority"]), "")
            output += f" | Priority: {priority_emoji} {fields['priority']}"
        
        # Add urgency if available
        if fields.get("urgency"):
            output += f" | Urgency: {fields['urgency']}"
        
        output += "\n"
        
        # Add people info
        people_info = []
        if fields.get("caller_name"):
            people_info.append(f"Caller: {fields['caller_name']}")
        if fields.get("agent_name"):
            people_info.append(f"Agent: {fields['agent_name']}")
        if people_info:
            output += f"   👤 {' | '.join(people_info)}\n"
        
        # Add org/team info
        org_info = []
        if fields.get("org_name"):
            org_info.append(f"Org: {fields['org_name']}")
        if fields.get("team_name"):
            org_info.append(f"Team: {fields['team_name']}")
        if org_info:
            output += f"   🏢 {' | '.join(org_info)}\n"
        
        # Add dates
        if fields.get("start_date"):
            output += f"   📅 Created: {fields['start_date']}\n"
        
        # Add SLA info if doing SLA analysis
        if intent.get("sla_analysis"):
            tto_passed = fields.get('sla_tto_passed', '')
            ttr_passed = fields.get('sla_ttr_passed', '')
            if tto_passed or ttr_passed:
                tto_icon = '✅' if tto_passed == 'yes' else '❌' if tto_passed == 'no' else '❓'
                ttr_icon = '✅' if ttr_passed == 'yes' else '❌' if ttr_passed == 'no' else '❓'
                output += f"   ⏰ SLA - TTO: {tto_icon} | TTR: {ttr_icon}\n"
        
        # Add class-specific info
        if self.class_name == "Change" and fields.get("outage") == "yes":
            output += f"   ⚠️ Planned Outage: Yes\n"
        
        output += "\n"
        return output

# =============================================================================
# Updated Handlers Using Smart Base
# =============================================================================

class UserRequestHandler(SmartHandlerBase):
    """Specialized handler for UserRequest queries"""
    
    def __init__(self, client: ITopClient):
        super().__init__(client, "UserRequest")
        
        # Field mappings based on docs.txt
        self.field_mappings = {
            # Status fields
            "status": "status",
            "operational_status": "operational_status", 
            "state": "status",
            
            # Priority/Urgency
            "priority": "priority",
            "urgency": "urgency",
            "impact": "impact",
            
            # People
            "caller": "caller_name",
            "agent": "agent_name",
            "approver": "approver_name",
            "user": "caller_name",
            
            # Organization/Team
            "organization": "org_name",
            "org": "org_name",
            "team": "team_name",
            
            # Service
            "service": "service_name",
            "category": "servicesubcategory_name",
            
            # Dates
            "start_date": "start_date",
            "end_date": "end_date",
            "close_date": "close_date",
            "resolution_date": "resolution_date",
            "assignment_date": "assignment_date",
            
            # SLA fields
            "sla_tto_passed": "sla_tto_passed",
            "sla_ttr_passed": "sla_ttr_passed",
            "tto_escalation_deadline": "tto_escalation_deadline",
            "ttr_escalation_deadline": "ttr_escalation_deadline",
            
            # Content
            "title": "title",
            "description": "description",
            "ref": "ref",
            "origin": "origin"
        }
        
        # Status value mappings
        self.status_values = {
            "new": "new",
            "assigned": "assigned", 
            "pending": "pending",
            "resolved": "resolved",
            "closed": "closed",
            "open": ["new", "assigned", "pending"],
            "active": ["new", "assigned", "pending", "in_progress"],
            "ongoing": ["new", "assigned", "pending", "in_progress"],
            "escalated": ["escalated_tto", "escalated_ttr"],
            "waiting": "waiting_for_approval",
            "approved": "approved",
            "rejected": "rejected",
            "in_progress": "in_progress",
            "awaiting_support": "awaiting_support"
        }
        
        # Priority mappings
        self.priority_values = {
            "critical": "1",
            "high": "2", 
            "medium": "3",
            "low": "4"
        }
        
    async def get_schema(self) -> Dict[str, Any]:
        """Get UserRequest schema by fetching one record with all fields"""
        operation = {
            "operation": "core/get",
            "class": self.class_name,
            "key": f"SELECT {self.class_name}",
            "output_fields": "*+",
            "limit": 1
        }
        
        result = await self.client.make_request(operation)
        
        if result.get("code") != 0:
            return {}
            
        objects = result.get("objects", {})
        if not objects:
            return {}
            
        first_obj = next(iter(objects.values()))
        if first_obj.get("code") == 0:
            fields = first_obj.get("fields", {})
            return {
                "field_names": list(fields.keys()),
                "sample_values": {k: str(v)[:100] if v else "" for k, v in fields.items()},
                "total_fields": len(fields)
            }
        
        return {}
    
    def parse_query_intent(self, query: str) -> Dict[str, Any]:
        """Parse natural language query for UserRequest-specific intent"""
        query_lower = query.lower()
        
        intent = {
            "action": "list",  # list, count, stats
            "filters": [],
            "grouping": None,
            "time_analysis": False,
            "sla_analysis": False,
            "comparison": False,
            "ordering": None  # Added for latest/newest ordering
        }
        
        # Detect action type - Enhanced comparison detection first with high priority
        is_comparison = any(word in query_lower for word in ["vs", "versus", "v/s", "compared to", "compare"])
        is_count_request = any(word in query_lower for word in ["count", "how many", "number of", "total count"]) and not is_comparison
        is_stats_request = any(word in query_lower for word in ["stats", "statistics", "breakdown", "by status", "group by"]) and not is_comparison
        
        # PRIORITY ORDER: comparison > count > stats > list
        # This ensures that queries like "count of tickets vs" are treated as comparisons
        if is_comparison:
            intent["action"] = "compare"
            intent["comparison"] = True
        elif is_count_request:
            intent["action"] = "count"
        elif is_stats_request:
            intent["action"] = "stats"
        
        # Enhanced SLA comparison detection - ONLY for explicit SLA mentions
        # Only apply SLA comparison when both "sla" AND comparison terms are present
        sla_comparison_patterns = [
            r"sla.*closed on time.*not closed on time",  # SLA with explicit timing language
            r"sla.*closed vs not closed",                # SLA mentioned with closed comparison
            r"closed vs not closed.*sla",                # Closed comparison with SLA mentioned
            r"sla.*on time vs not on time",              # SLA with timing comparison
            r"on time vs not on time.*sla",              # Timing comparison with SLA
            r"met sla vs missed sla",                    # Direct SLA comparison
            r"sla met vs sla missed",                    # Direct SLA comparison
            r"support tickets closed on time vs not closed on time based on sla",
            r"closed vs not closed on time.*sla", 
            r"closed vs not closed.*on time.*sla",
            r".*closed on time.*not closed on time.*based on sla.*",  # More flexible pattern
            r".*sla.*closed on time.*not closed on time.*"   # More flexible pattern
        ]
        
        # Check if this is an SLA-related comparison (must have explicit SLA mention)
        is_sla_comparison = False
        if "sla" in query_lower:  # Only check patterns if SLA is mentioned
            for pattern in sla_comparison_patterns:
                if re.search(pattern, query_lower, re.IGNORECASE):
                    is_sla_comparison = True
                    intent["action"] = "compare"
                    intent["comparison"] = True
                    intent["sla_analysis"] = True
                    break
        
        # Detect SLA-related queries
        if any(word in query_lower for word in ["sla", "on time", "late", "overdue", "deadline", "closed on time", "not closed on time"]):
            intent["sla_analysis"] = True
            intent["time_analysis"] = True
        
        # Detect ordering requirements
        if "latest" in query_lower or "newest" in query_lower or "recent" in query_lower:
            intent["ordering"] = "start_date DESC"
        
        # Extract filters
        filters = self._extract_filters(query_lower)
        intent["filters"] = filters
        
        # Detect grouping using smart engine
        intent["grouping"] = SmartGroupingEngine.detect_grouping(query_lower, self.class_name)
        
        return intent
    
    def _extract_filters(self, query_lower: str) -> List[Dict[str, Any]]:
        """Extract filters from query using universal filter engine"""
        # Use the universal filter engine for consistent filtering across all classes
        return SmartFilterEngine.extract_filters(query_lower, self.class_name)
    
    def build_oql_query(self, intent: Dict[str, Any]) -> str:
        """Build OQL query for UserRequests using smart query builder"""
        return SmartQueryBuilder.build_oql_query(self.class_name, intent["filters"])
    
    def determine_output_fields(self, intent: Dict[str, Any]) -> str:
        """Determine which fields to return based on query intent"""
        if intent["action"] == "count":
            if intent["grouping"]:
                return f"id,{intent['grouping']}"
            else:
                return "id"
        
        # For detailed queries, return key fields
        key_fields = [
            "id", "ref", "title", "status", "priority", "urgency",
            "caller_name", "agent_name", "org_name", "team_name",
            "start_date", "resolution_date", "close_date"
        ]
        
        # Add SLA fields if doing SLA analysis
        if intent["sla_analysis"]:
            sla_fields = [
                "sla_tto_passed", "sla_ttr_passed", 
                "tto_escalation_deadline", "ttr_escalation_deadline"
            ]
            key_fields.extend(sla_fields)
        
        return ",".join(key_fields)
    
    async def process_query(self, query: str, limit: int = 100) -> str:
        """Main entry point for processing UserRequest queries"""
        try:
            # Parse query intent
            intent = self.parse_query_intent(query)
            
            # Handle comparison queries (e.g., "closed vs open")
            if intent["comparison"]:
                return await self._handle_comparison_query(query, intent, limit)
            
            # Build OQL query
            oql_query = self.build_oql_query(intent)
            output_fields = self.determine_output_fields(intent)
            
            # Execute query
            operation = {
                "operation": "core/get",
                "class": self.class_name,
                "key": oql_query,
                "output_fields": output_fields,
                "limit": limit
            }
            
            result = await self.client.make_request(operation)
            
            if result.get("code") != 0:
                return f"❌ **Query Error**: {result.get('message', 'Unknown error')}"
            
            # Format results
            return self._format_results(result, intent, query, oql_query)
            
        except Exception as e:
            return f"❌ **UserRequest Query Error**: {str(e)}"
    

    


    def _format_results(self, result: dict, intent: Dict[str, Any], query: str, oql_query: str) -> str:
        """Universal results formatter"""
        if result.get("code") != 0:
            return f"❌ **{self.class_name} Query Error**: {result.get('message', 'Unknown error')}"
        
        objects = result.get("objects", {})
        message = result.get("message", "")
        total_count = _extract_count_from_message(message)
        
        # Get appropriate emoji for class
        emoji_map = {
            "UserRequest": "🎫",
            "Ticket": "🎫", 
            "Change": "🔄",
            "Incident": "🚨",
            "Problem": "🔍"
        }
        emoji = emoji_map.get(self.class_name, "📋")
        
        output = f"**{emoji} {self.class_name} Query Results**\n\n"
        output += f"**Query**: \"{query}\"\n"
        output += f"**OQL Used**: `{oql_query}`\n"
        
        if intent["filters"]:
            filter_descriptions = [f.get("display_name", "unknown filter") for f in intent["filters"] if f and isinstance(f, dict)]
            if filter_descriptions:
                output += f"**Filters Applied**: {', '.join(filter_descriptions)}\n"
        
        if total_count is not None:
            output += f"**Total Found**: {total_count}\n"
        output += f"**Returned**: {len(objects) if objects else 0}\n\n"
        
        if not objects:
            return output + f"No {self.class_name.lower()}s found matching your criteria."
        
        if intent["action"] == "count":
            return output + f"**Total {self.class_name}s**: {total_count or (len(objects) if objects else 0)}"
        elif intent["action"] == "group":
            return output + SmartGroupingEngine.format_grouped_results(objects, intent["grouping"], self.class_name)
        else:
            return output + self._format_detailed_results(objects, intent)
    
    def _format_detailed_results(self, objects: dict, intent: Dict[str, Any]) -> str:
        """Universal detailed results formatter"""
        output = ""
        
        # Group by type if it's a generic Ticket query
        if self.class_name == "Ticket":
            type_groups = {}
            for obj_key, obj_data in objects.items():
                if obj_data.get("code") == 0:
                    fields = obj_data.get("fields", {})
                    ticket_type = fields.get("finalclass", "Unknown")
                    if ticket_type not in type_groups:
                        type_groups[ticket_type] = []
                    type_groups[ticket_type].append((obj_key, obj_data))
            
            for ticket_type, tickets in type_groups.items():
                if tickets:
                    output += f"### {ticket_type} ({len(tickets)})\n"
                    output += self._format_ticket_group(tickets)
                    output += "\n"
        else:
            # Single class formatting
            for i, (obj_key, obj_data) in enumerate(objects.items(), 1):
                if obj_data.get("code") == 0:
                    output += self._format_single_record(i, obj_key, obj_data, intent)
        
        return output
    
    def _format_ticket_group(self, tickets: list) -> str:
        """Format a group of tickets"""
        output = ""
        for i, (obj_key, obj_data) in enumerate(tickets, 1):
            output += self._format_single_record(i, obj_key, obj_data, {})
        return output
    
    def _format_single_record(self, index: int, obj_key: str, obj_data: dict, intent: Dict[str, Any]) -> str:
        """Format a single record universally"""
        fields = obj_data.get("fields", {})
        
        # Get key identifiers
        ref = fields.get("ref", obj_key)
        title = fields.get("title", fields.get("name", fields.get("friendlyname", "No title")))
        
        # Get status (adapt to class)
        status = fields.get("status", fields.get("operational_status", "Unknown"))
        
        output = f"{index}. **{ref}** - {title}\n"
        output += f"   Status: {status}"
        
        # Add priority if available
        if fields.get("priority"):
            priority_emoji = {"1": "🔴", "2": "🟡", "3": "🟢", "4": "⚪"}.get(str(fields["priority"]), "")
            output += f" | Priority: {priority_emoji} {fields['priority']}"
        
        # Add urgency if available
        if fields.get("urgency"):
            output += f" | Urgency: {fields['urgency']}"
        
        output += "\n"
        
        # Add people info
        people_info = []
        if fields.get("caller_name"):
            people_info.append(f"Caller: {fields['caller_name']}")
        if fields.get("agent_name"):
            people_info.append(f"Agent: {fields['agent_name']}")
        if people_info:
            output += f"   👤 {' | '.join(people_info)}\n"
        
        # Add org/team info
        org_info = []
        if fields.get("org_name"):
            org_info.append(f"Org: {fields['org_name']}")
        if fields.get("team_name"):
            org_info.append(f"Team: {fields['team_name']}")
        if org_info:
            output += f"   🏢 {' | '.join(org_info)}\n"
        
        # Add dates
        if fields.get("start_date"):
            output += f"   📅 Created: {fields['start_date']}\n"
        
        # Add SLA info if doing SLA analysis
        if intent.get("sla_analysis"):
            tto_passed = fields.get('sla_tto_passed', '')
            ttr_passed = fields.get('sla_ttr_passed', '')
            if tto_passed or ttr_passed:
                tto_icon = '✅' if tto_passed == 'yes' else '❌' if tto_passed == 'no' else '❓'
                ttr_icon = '✅' if ttr_passed == 'yes' else '❌' if ttr_passed == 'no' else '❓'
                output += f"   ⏰ SLA - TTO: {tto_icon} | TTR: {ttr_icon}\n"
        
        # Add class-specific info
        if self.class_name == "Change" and fields.get("outage") == "yes":
            output += f"   ⚠️ Planned Outage: Yes\n"
        
        output += "\n"
        return output

class TicketHandler(SmartHandlerBase):
    """Specialized handler for generic Ticket queries - covers all ticket types"""
    
    def __init__(self, client: ITopClient):
        super().__init__(client, "Ticket")
        self.schema_fields = {
            # Core ticket fields from documentation
            "ref": "Ticket reference",
            "title": "Ticket title",
            "description": "Ticket description", 
            "operational_status": "Status (ongoing/resolved/closed)",
            "start_date": "Start date",
            "end_date": "End date",
            "close_date": "Close date",
            "last_update": "Last update",
            
            # People and teams
            "org_name": "Organization",
            "caller_name": "Caller",
            "team_name": "Team",
            "agent_name": "Agent",
            
            # Sub-class identification
            "finalclass": "Ticket type (UserRequest/Change/Incident/Problem)",
            "friendlyname": "Display name"
        }
    
    def parse_query_intent(self, query: str) -> Dict[str, Any]:
        """Parse query intent for tickets"""
        query_lower = query.lower()
        
        intent = {
            "action": "list",
            "filters": [],
            "grouping": None,
            "fields": [],
            "comparison": False,
            "sla_analysis": False
        }
        
        # Detect action type - Enhanced comparison detection first with high priority
        is_comparison = any(word in query_lower for word in ["vs", "versus", "v/s", "compared to"])
        is_count_request = any(word in query_lower for word in ["count", "how many", "total"]) and not is_comparison
        is_grouping = any(word in query_lower for word in ["group by", "grouped by", "breakdown", "summary", "organization wise", "org wise", "by organization", "by org"]) and not is_comparison
        
        # PRIORITY ORDER: comparison > count > grouping > list
        if is_comparison:
            intent["action"] = "compare"
            intent["comparison"] = True
        elif is_count_request:
            intent["action"] = "count"
        elif is_grouping:
            intent["action"] = "group"
            intent["grouping"] = SmartGroupingEngine.detect_grouping(query_lower, self.class_name)
        
        # Add filters using smart engine (NO SLA logic for generic tickets)
        intent["filters"] = SmartFilterEngine.extract_filters(query_lower, self.class_name)
        
        return intent
    
    def build_oql_query(self, intent: Dict[str, Any]) -> str:
        """Build OQL query for tickets using smart query builder"""
        return SmartQueryBuilder.build_oql_query(self.class_name, intent["filters"])
    
    def determine_output_fields(self, intent: Dict[str, Any]) -> str:
        """Determine output fields"""
        if intent["action"] == "count":
            if intent["grouping"]:
                return f"id,{intent['grouping']}"
            else:
                return "id"
        
        # Return all fields for detailed view since Ticket covers multiple classes
        return "*+"
    
    async def process_query(self, query: str, limit: int = 100) -> str:
        """Process ticket query with multi-class awareness"""
        query_lower = query.lower()
        
        # SPECIAL HANDLING: If query mentions "critical" tickets, delegate to UserRequest 
        # since Ticket class doesn't have priority field but UserRequest does
        if "critical" in query_lower and ("ticket" in query_lower or "tickets" in query_lower):
            user_request_handler = UserRequestHandler(self.client)
            modified_query = query.replace("ticket", "user request").replace("tickets", "user requests")
            result = await user_request_handler.process_query(modified_query, limit)
            # Update the result header to reflect it's showing UserRequests (which are tickets)
            result = result.replace("UserRequest Query Results", "Critical Ticket Query Results (UserRequests)")
            result += f"\n**Note**: Showing UserRequests since generic Ticket class doesn't have priority field. Other ticket types (Incident, Problem, Change) would need separate queries."
            return result
        
        intent = self.parse_query_intent(query)
        
        # Handle comparison queries using base class logic (NO SLA logic for generic tickets)
        if intent["comparison"]:
            return await super()._handle_comparison_query(query, intent, limit)
        
        # Build OQL query
        oql_query = self.build_oql_query(intent)
        output_fields = self.determine_output_fields(intent)
        
        # Execute query
        operation = {
            "operation": "core/get",
            "class": self.class_name,
            "key": oql_query,
            "output_fields": output_fields,
            "limit": limit
        }
        
        result = await self.client.make_request(operation)
        return self._format_results(result, intent, query, oql_query)
    
    def _parse_query_intent(self, query: str) -> Dict[str, Any]:
        """Parse query intent for tickets"""
        query_lower = query.lower()
        
        intent = {
            "action": "list",
            "filters": [],
            "grouping": None,
            "fields": []
        }
        
        # Determine action
        if any(word in query_lower for word in ["count", "how many", "total"]):
            intent["action"] = "count"
        elif any(word in query_lower for word in ["group by", "breakdown", "summary", "organization wise", "org wise", "by organization", "by org"]):
            intent["action"] = "group"
            intent["grouping"] = SmartGroupingEngine.detect_grouping(query_lower, self.class_name)
        
        # Add filters using smart engine
        intent["filters"] = SmartFilterEngine.extract_filters(query_lower, self.class_name)
        
        return intent
    
    def _extract_filters(self, query_lower: str) -> List[Dict[str, Any]]:
        """Extract filters from query using smart filter engine"""
        return SmartFilterEngine.extract_filters(query_lower, self.class_name)
    
    def _format_results(self, result: dict, intent: Dict[str, Any], query: str, oql_query: str) -> str:
        """Format ticket results with multi-class awareness"""
        if result.get("code") != 0:
            return f"❌ **Ticket Query Error**: {result.get('message', 'Unknown error')}"
        
        objects = result.get("objects", {})
        message = result.get("message", "")
        total_count = _extract_count_from_message(message)
        
        output = f"**🎫 Ticket Query Results**\n\n"
        output += f"**Query**: \"{query}\"\n"
        output += f"**OQL Used**: `{oql_query}`\n"
        
        if intent["filters"]:
            filter_descriptions = [f.get("display_name", "unknown filter") for f in intent["filters"] if f and isinstance(f, dict)]
            if filter_descriptions:
                output += f"**Filters Applied**: {', '.join(filter_descriptions)}\n"
        
        if total_count is not None:
            output += f"**Total Found**: {total_count}\n"
        output += f"**Returned**: {len(objects) if objects else 0}\n\n"
        
        if not objects:
            return output + "No tickets found matching your criteria."
        
        if intent["action"] == "count":
            return output + f"**Total Tickets**: {total_count or (len(objects) if objects else 0)}"
        elif intent["action"] == "group":
            return output + SmartGroupingEngine.format_grouped_results(objects, intent["grouping"], self.class_name)
        else:
            return output + self._format_detailed_results(objects)
    
    def _format_detailed_results(self, objects: dict) -> str:
        """Format detailed ticket results"""
        output = ""
        
        # Group by ticket type for better organization
        type_groups = {}
        for obj_key, obj_data in objects.items():
            if obj_data.get("code") == 0:
                fields = obj_data.get("fields", {})
                ticket_type = fields.get("finalclass", "Unknown")
                if ticket_type not in type_groups:
                    type_groups[ticket_type] = []
                type_groups[ticket_type].append((obj_key, obj_data))
        
        for ticket_type, tickets in type_groups.items():
            if tickets:
                output += f"### {ticket_type} ({len(tickets)})\n"
                
                for i, (obj_key, obj_data) in enumerate(tickets, 1):
                    fields = obj_data.get("fields", {})
                    
                    ref = fields.get("ref", obj_key)
                    title = fields.get("title", "No title")
                    status = fields.get("operational_status", "Unknown")
                    
                    output += f"{i}. **{ref}** - {title}\n"
                    output += f"   Status: {status}\n"
                    
                    if fields.get("caller_name"):
                        output += f"   Caller: {fields['caller_name']}\n"
                    if fields.get("org_name"):
                        output += f"   Organization: {fields['org_name']}\n"
                    if fields.get("agent_name"):
                        output += f"   Agent: {fields['agent_name']}\n"
                    
                    output += "\n"
                
                output += "\n"
        
        return output

class ChangeHandler(SmartHandlerBase):
    """Specialized handler for Change requests and their subtypes"""
    
    def __init__(self, client: ITopClient):
        super().__init__(client, "Change")
        self.schema_fields = {
            # Inherited from Ticket
            "ref": "Change reference",
            "title": "Change title", 
            "description": "Change description",
            "operational_status": "Operational status",
            "status": "Change status (new/validated/approved/implemented/closed)",
            
            # Change-specific fields
            "creation_date": "Creation date",
            "impact": "Impact description",
            "outage": "Planned outage (yes/no)",
            "fallback": "Fallback plan",
            "reason": "Rejection reason",
            
            # People involved
            "caller_name": "Caller",
            "requestor_id": "Requestor", 
            "supervisor_group_name": "Supervisor team",
            "supervisor_id": "Supervisor",
            "manager_group_name": "Manager team",
            "manager_id": "Manager",
            "agent_name": "Assigned agent",
            
            # Relationships
            "parent_name": "Parent change",
            "related_request_list": "Related user requests",
            "related_incident_list": "Related incidents", 
            "related_problems_list": "Related problems",
            "child_changes_list": "Child changes",
            
            # Sub-class info
            "finalclass": "Change type (NormalChange/EmergencyChange/RoutineChange)"
        }
    
    async def process_query(self, query: str, limit: int = 100) -> str:
        """Process change query"""
        intent = self._parse_query_intent(query)
        
        oql_query = self.build_oql_query(intent)
        output_fields = self.determine_output_fields(intent)
        
        operation = {
            "operation": "core/get",
            "class": self.class_name,
            "key": oql_query,
            "output_fields": output_fields,
            "limit": limit
        }
        
        result = await self.client.make_request(operation)
        return self._format_results(result, intent, query, oql_query)
    
    def _parse_query_intent(self, query: str) -> Dict[str, Any]:
        """Parse change query intent"""
        query_lower = query.lower()
        
        intent = {
            "action": "list",
            "filters": [],
            "grouping": None,
            "fields": []
        }
        
        # Determine action
        if any(word in query_lower for word in ["count", "how many", "total"]):
            intent["action"] = "count"
        elif any(word in query_lower for word in ["group by", "breakdown", "summary"]):
            intent["action"] = "group"
            intent["grouping"] = SmartGroupingEngine.detect_grouping(query_lower, self.class_name)
        
        intent["filters"] = SmartFilterEngine.extract_filters(query_lower, self.class_name)
        return intent
    
    def build_oql_query(self, intent: Dict[str, Any]) -> str:
        """Build OQL query for changes using smart query builder"""
        return SmartQueryBuilder.build_oql_query(self.class_name, intent["filters"])
    
    def determine_output_fields(self, intent: Dict[str, Any]) -> str:
        """Determine output fields for changes"""
        if intent["action"] == "count":
            return f"id,{intent['grouping']}" if intent["grouping"] else "id"
        
        # Return comprehensive fields for changes
        return "*+"
    
    def _format_results(self, result: dict, intent: Dict[str, Any], query: str, oql_query: str) -> str:
        """Format change results"""
        if result.get("code") != 0:
            return f"❌ **Change Query Error**: {result.get('message', 'Unknown error')}"
        
        objects = result.get("objects", {})
        message = result.get("message", "")
        total_count = _extract_count_from_message(message)
        
        output = f"**🔄 Change Request Results**\n\n"
        output += f"**Query**: \"{query}\"\n"
        output += f"**OQL Used**: `{oql_query}`\n"
        
        if intent["filters"]:
            filter_descriptions = [f.get("display_name", "unknown filter") for f in intent["filters"] if f and isinstance(f, dict)]
            if filter_descriptions:
                output += f"**Filters Applied**: {', '.join(filter_descriptions)}\n"
        
        if total_count is not None:
            output += f"**Total Found**: {total_count}\n"
        output += f"**Returned**: {len(objects) if objects else 0}\n\n"
        
        if not objects:
            return output + "No change requests found matching your criteria."
        
        if intent["action"] == "count":
            return output + f"**Total Changes**: {total_count or (len(objects) if objects else 0)}"
        elif intent["action"] == "group":
            return output + SmartGroupingEngine.format_grouped_results(objects, intent["grouping"], self.class_name)
        else:
            return output + self._format_detailed_results(objects)
    
    def _format_detailed_results(self, objects: dict) -> str:
        """Format detailed change results"""
        output = ""
        
        for i, (obj_key, obj_data) in enumerate(objects.items(), 1):
            if obj_data.get("code") == 0:
                fields = obj_data.get("fields", {})
                
                ref = fields.get("ref", obj_key)
                title = fields.get("title", "No title")
                status = fields.get("status", "Unknown")
                change_type = fields.get("finalclass", "Change")
                
                output += f"{i}. **{ref}** - {title}\n"
                output += f"   Type: {change_type}\n"
                output += f"   Status: {status}\n"
                output += f"   Operational Status: {fields.get('operational_status', 'Unknown')}\n"
                
                if fields.get("caller_name"):
                    output += f"   Caller: {fields['caller_name']}\n"
                if fields.get("org_name"):
                    output += f"   Organization: {fields['org_name']}\n"
                if fields.get("creation_date"):
                    output += f"   Created: {fields['creation_date']}\n"
                if fields.get("outage") == "yes":
                    output += f"   ⚠️ Planned Outage: Yes\n"
                if fields.get("impact"):
                    output += f"   Impact: {fields['impact']}\n"
                
                output += "\n"
        
        return output

class IncidentHandler(SmartHandlerBase):
    """Specialized handler for Incident tickets"""
    
    def __init__(self, client: ITopClient):
        super().__init__(client, "Incident")
        self.schema_fields = {
            # Inherited from Ticket
            "ref": "Incident reference",
            "title": "Incident title",
            "description": "Incident description",
            "operational_status": "Operational status",
            "status": "Incident status (new/assigned/resolved/closed)",
            
            # Incident-specific fields
            "priority": "Priority (1-4)",
            "urgency": "Urgency (1-4)", 
            "impact": "Impact (1-3)",
            "service_name": "Affected service",
            "servicesubcategory_name": "Service subcategory",
            "assignment_date": "Assignment date",
            "resolution_date": "Resolution date",
            "resolution_code": "Resolution code",
            "solution": "Solution description",
            "time_spent": "Time spent on resolution",
            "user_satisfaction": "User satisfaction (1-4)",
            "category": "Category (operational/security)",
            "source": "Source (opensearch/wazuh/zabbix)",
            
            # People
            "caller_name": "Caller",
            "agent_name": "Assigned agent",
            "org_name": "Organization",
            "team_name": "Team",
            
            # Relationships
            "parent_incident_id": "Parent incident",
            "parent_problem_id": "Parent problem",
            "parent_change_id": "Parent change",
            "related_request_list": "Related user requests",
            "child_incidents_list": "Child incidents"
        }
    
    async def process_query(self, query: str, limit: int = 100) -> str:
        """Process incident query with error handling for missing class"""
        try:
            intent = self._parse_query_intent(query)
            
            oql_query = self.build_oql_query(intent)
            output_fields = self.determine_output_fields(intent)
            
            operation = {
                "operation": "core/get",
                "class": self.class_name,
                "key": oql_query,
                "output_fields": output_fields,
                "limit": limit
            }
            
            result = await self.client.make_request(operation)
            
            # Check if class doesn't exist
            if result.get("code") != 0:
                error_msg = result.get("message", "Unknown error")
                if "unknown class" in error_msg.lower() or "class not found" in error_msg.lower():
                    return f"⚠️ **Incident Class Not Available**: The Incident class may not be configured in your iTop instance.\n\n**Error**: {error_msg}\n\n**Suggestion**: Use the generic Ticket handler instead by searching for 'tickets' or contact your iTop administrator to configure the Incident class."
                return f"❌ **Incident Query Error**: {error_msg}"
            
            return self._format_results(result, intent, query, oql_query)
            
        except Exception as e:
            return f"❌ **Incident Handler Error**: {str(e)}"
    
    def _parse_query_intent(self, query: str) -> Dict[str, Any]:
        """Parse incident query intent"""
        query_lower = query.lower()
        
        intent = {
            "action": "list",
            "filters": [],
            "grouping": None,
            "fields": []
        }
        
        # Determine action
        if any(word in query_lower for word in ["count", "how many", "total"]):
            intent["action"] = "count"
        elif any(word in query_lower for word in ["group by", "breakdown", "summary", "organization wise", "org wise", "by organization", "by org"]):
            intent["action"] = "group"
            if "priority" in query_lower:
                intent["grouping"] = "priority"
            elif "status" in query_lower:
                intent["grouping"] = "status"
            elif "category" in query_lower:
                intent["grouping"] = "category"
            elif "source" in query_lower:
                intent["grouping"] = "source"
        
        intent["filters"] = self._extract_filters(query_lower)
        return intent
    
    def _extract_filters(self, query_lower: str) -> List[Dict[str, Any]]:
        """Extract incident-specific filters using universal filter engine"""
        # Use the universal filter engine for consistent filtering across all classes
        return SmartFilterEngine.extract_filters(query_lower, self.class_name)
    
    def build_oql_query(self, intent: Dict[str, Any]) -> str:
        """Build OQL query for incidents"""
        base_query = f"SELECT {self.class_name}"
        conditions = []
        
        for filter_info in intent["filters"]:
            field = filter_info["field"]
            operator = filter_info["operator"]
            value = filter_info["value"]
            
            if operator in ["=", "!=", ">", "<", ">=", "<="]:
                conditions.append(f"{field} {operator} '{value}'")
        
        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)
        
        return base_query
    
    def determine_output_fields(self, intent: Dict[str, Any]) -> str:
        """Determine output fields for incidents"""
        if intent["action"] == "count":
            return f"id,{intent['grouping']}" if intent["grouping"] else "id"
        
        return "*+"
    
    def _format_results(self, result: dict, intent: Dict[str, Any], query: str, oql_query: str) -> str:
        """Format incident results"""
        if result.get("code") != 0:
            return f"❌ **Incident Query Error**: {result.get('message', 'Unknown error')}"
        
        objects = result.get("objects", {})
        message = result.get("message", "")
        total_count = _extract_count_from_message(message)
        
        output = f"**🚨 Incident Results**\n\n"
        output += f"**Query**: \"{query}\"\n"
        output += f"**OQL Used**: `{oql_query}`\n"
        
        if intent.get("filters"):
            filter_descriptions = [f.get("display_name", "unknown filter") for f in intent["filters"] if f and isinstance(f, dict)]
            if filter_descriptions:
                output += f"**Filters Applied**: {', '.join(filter_descriptions)}\n"
        
        if total_count is not None:
            output += f"**Total Found**: {total_count}\n"
        output += f"**Returned**: {len(objects) if objects else 0}\n\n"
        
        if not objects:
            return output + "No incidents found matching your criteria."
        
        if intent["action"] == "count":
            return output + f"**Total Incidents**: {total_count or (len(objects) if objects else 0)}"
        elif intent["action"] == "group":
            return output + self._format_grouped_results(objects, intent["grouping"])
        else:
            return output + self._format_detailed_results(objects)
    
    def _format_grouped_results(self, objects: dict, group_field: str) -> str:
        """Format grouped incident results - Fixed"""
        if not objects:
            return f"**No data to group by {group_field}**\n"
            
        groups = {}
        for obj_data in objects.values():
            if obj_data.get("code") == 0:
                fields = obj_data.get("fields", {})
                group_value = fields.get(group_field, "Unknown")
                groups[group_value] = groups.get(group_value, 0) + 1
        
        output = f"**Breakdown by {group_field}:**\n"
        for group, count in sorted(groups.items()):
            output += f"- {group}: {count}\n"
        
        return output
    
    def _format_detailed_results(self, objects: dict) -> str:
        """Format detailed incident results"""
        output = ""
        
        for i, (obj_key, obj_data) in enumerate(objects.items(), 1):
            if obj_data.get("code") == 0:
                fields = obj_data.get("fields", {})
                
                ref = fields.get("ref", obj_key)
                title = fields.get("title", "No title")
                status = fields.get("status", "Unknown")
                priority = fields.get("priority", "Unknown")
                
                output += f"{i}. **{ref}** - {title}\n"
                output += f"   Status: {status} | Priority: {priority}\n"
                
                if fields.get("category"):
                    output += f"   Category: {fields['category']}\n"
                if fields.get("caller_name"):
                    output += f"   Caller: {fields['caller_name']}\n"
                if fields.get("agent_name"):
                    output += f"   Agent: {fields['agent_name']}\n"
                if fields.get("source"):
                    output += f"   Source: {fields['source']}\n"
                
                output += "\n"
        
        return output

class ProblemHandler(SmartHandlerBase):
    """Specialized handler for Problem tickets"""
    
    def __init__(self, client: ITopClient):
        super().__init__(client, "Problem")
        self.schema_fields = {
            # Inherited from Ticket
            "ref": "Problem reference",
            "title": "Problem title",
            "description": "Problem description",
            "operational_status": "Operational status",
            "status": "Problem status (new/assigned/resolved/closed)",
            
            # Problem-specific fields
            "priority": "Priority (1-4)",
            "urgency": "Urgency (1-4)",
            "impact": "Impact (1-3)",
            "service_name": "Affected service",
            "servicesubcategory_name": "Service subcategory",
            "product": "Product",
            "assignment_date": "Assignment date",
            "resolution_date": "Resolution date",
            
            # People
            "caller_name": "Caller",
            "agent_name": "Assigned agent",
            "org_name": "Organization",
            "team_name": "Team",
            
            # Relationships
            "related_change_id": "Related change",
            "knownerrors_list": "Known errors",
            "related_request_list": "Related user requests", 
            "related_incident_list": "Related incidents"
        }
    
    async def process_query(self, query: str, limit: int = 100) -> str:
        """Process problem query with error handling for missing class"""
        try:
            intent = self._parse_query_intent(query)
            
            oql_query = self.build_oql_query(intent)
            output_fields = self.determine_output_fields(intent)
            
            operation = {
                "operation": "core/get",
                "class": self.class_name,
                "key": oql_query,
                "output_fields": output_fields,
                "limit": limit
            }
            
            result = await self.client.make_request(operation)
            
            # Check if class doesn't exist
            if result.get("code") != 0:
                error_msg = result.get("message", "Unknown error")
                if "unknown class" in error_msg.lower() or "class not found" in error_msg.lower():
                    return f"⚠️ **Problem Class Not Available**: The Problem class may not be configured in your iTop instance.\n\n**Error**: {error_msg}\n\n**Suggestion**: Use the generic Ticket handler instead by searching for 'tickets' or contact your iTop administrator to configure the Problem class."
                return f"❌ **Problem Query Error**: {error_msg}"
            
            return self._format_results(result, intent, query, oql_query)
            
        except Exception as e:
            return f"❌ **Problem Handler Error**: {str(e)}"
    
    def _parse_query_intent(self, query: str) -> Dict[str, Any]:
        """Parse problem query intent"""
        query_lower = query.lower()
        
        intent = {
            "action": "list",
            "filters": [],
            "grouping": None,
            "fields": []
        }
        
        # Determine action
        if any(word in query_lower for word in ["count", "how many", "total"]):
            intent["action"] = "count"
        elif any(word in query_lower for word in ["group by", "breakdown", "summary"]):
            intent["action"] = "group"
            if "priority" in query_lower:
                intent["grouping"] = "priority"
            elif "status" in query_lower:
                intent["grouping"] = "status"
        
        intent["filters"] = self._extract_filters(query_lower)
        return intent
    
    def _extract_filters(self, query_lower: str) -> List[Dict[str, Any]]:
        """Extract problem-specific filters using universal filter engine"""
        # Use the universal filter engine for consistent filtering across all classes
        return SmartFilterEngine.extract_filters(query_lower, self.class_name)
    
    def build_oql_query(self, intent: Dict[str, Any]) -> str:
        """Build OQL query for problems"""
        base_query = f"SELECT {self.class_name}"
        conditions = []
        
        for filter_info in intent["filters"]:
            field = filter_info["field"]
            operator = filter_info["operator"]
            value = filter_info["value"]
            
            if operator in ["=", "!=", ">", "<", ">=", "<="]:
                conditions.append(f"{field} {operator} '{value}'")
        
        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)
        
        return base_query
    
    def determine_output_fields(self, intent: Dict[str, Any]) -> str:
        """Determine output fields for problems"""
        if intent["action"] == "count":
            return f"id,{intent['grouping']}" if intent["grouping"] else "id"
        
        return "*+"
    
    def _format_results(self, result: dict, intent: Dict[str, Any], query: str, oql_query: str) -> str:
        """Format problem results"""
        if result.get("code") != 0:
            return f"❌ **Problem Query Error**: {result.get('message', 'Unknown error')}"
        
        objects = result.get("objects", {})
        message = result.get("message", "")
        total_count = _extract_count_from_message(message)
        
        output = f"**🔍 Problem Analysis Results**\n\n"
        output += f"**Query**: \"{query}\"\n"
        output += f"**OQL Used**: `{oql_query}`\n"
        
        if intent["filters"]:
            filter_descriptions = [f.get("display_name", "unknown filter") for f in intent["filters"] if f and isinstance(f, dict)]
            if filter_descriptions:
                output += f"**Filters Applied**: {', '.join(filter_descriptions)}\n"
        
        if total_count is not None:
            output += f"**Total Found**: {total_count}\n"
        output += f"**Returned**: {len(objects) if objects else 0}\n\n"
        
        if not objects:
            return output + "No problems found matching your criteria."
        
        if intent["action"] == "count":
            return output + f"**Total Problems**: {total_count or (len(objects) if objects else 0)}"
        elif intent["action"] == "group":
            return output + self._format_grouped_results(objects, intent["grouping"])
        else:
            return output + self._format_detailed_results(objects)
    
    def _format_grouped_results(self, objects: dict, group_field: str) -> str:
        """Format grouped problem results"""
        if not objects:
            return f"**No data to group by {group_field}**\n"
            
        groups = {}
        for obj_data in objects.values():
            if obj_data.get("code") == 0:
                fields = obj_data.get("fields", {})
                group_value = fields.get(group_field, "Unknown")
                groups[group_value] = groups.get(group_value, 0) + 1
        
        output = f"**Breakdown by {group_field}:**\n"
        for group, count in sorted(groups.items()):
            output += f"- {group}: {count}\n"
        
        return output
    
    def _format_detailed_results(self, objects: dict) -> str:
        """Format detailed problem results"""
        output = ""
        
        for i, (obj_key, obj_data) in enumerate(objects.items(), 1):
            if obj_data.get("code") == 0:
                fields = obj_data.get("fields", {})
                
                ref = fields.get("ref", obj_key)
                title = fields.get("title", "No title")
                status = fields.get("status", "Unknown")
                priority = fields.get("priority", "Unknown")
                
                # Priority emoji mapping
                priority_emoji = {"1": "🔴", "2": "🟡", "3": "🟢", "4": "⚪"}.get(str(priority), "")
                
                output += f"{i}. **{ref}** - {title}\n"
                output += f"   Status: {status}\n"
                output += f"   Priority: {priority_emoji} {priority}\n"
                
                if fields.get("urgency"):
                    output += f"   Urgency: {fields['urgency']}\n"
                if fields.get("impact"):
                    output += f"   Impact: {fields['impact']}\n"
                if fields.get("caller_name"):
                    output += f"   Caller: {fields['caller_name']}\n"
                if fields.get("agent_name"):
                    output += f"   Agent: {fields['agent_name']}\n"
                if fields.get("service_name"):
                    output += f"   Service: {fields['service_name']}\n"
                if fields.get("product"):
                    output += f"   Product: {fields['product']}\n"
                
                output += "\n"
        
        return output

class PCHandler(SmartHandlerBase):
    """Handler for PC (Personal Computer) queries"""
    
    def __init__(self, client: ITopClient):
        super().__init__(client, "PC")
        
        # Field mappings based on docs.txt
        self.field_mappings = {
            # Core fields
            "name": "name",
            "description": "description",
            "organization": "org_name",
            "org": "org_name",
            
            # Status and lifecycle
            "status": "status",  # stock/implementation/production/obsolete
            "business_criticality": "business_criticity",  # critical/high/medium/low
            "move_to_production": "move2production",
            
            # Hardware details
            "serial_number": "serialnumber",
            "brand": "brand_name",
            "model": "model_name",
            "asset_number": "asset_number",
            "cpu": "cpu",
            "ram": "ram",
            "type": "type",  # desktop/laptop
            
            # Location and ownership relationships
            "location": "location_name",
            "user": "user_friendlyname",  # Person assigned to PC
            "owner": "owner_friendlyname",  # Team that owns the PC
            "contingency": "contingency_friendlyname",  # Backup PC
            
            # OS information (detailed)
            "os_family": "osfamily_name",
            "os_version": "osversion_name", 
            "os_license": "oslicence_name",
            "os_comment": "ocs_oscomment",
            
            # Security ratings
            "confidentiality": "confidentiality",  # 1-4
            "integrity": "integrity",  # 1-4  
            "availability": "availability",  # 1-4
            "score": "score",
            "cvss": "cvss",
            
            # Dates
            "purchase_date": "purchase_date",
            "warranty_end": "end_of_warranty",
            
            # Network and relationships
            "contacts": "contacts_list",
            "softwares": "softwares_list",
            "tickets": "tickets_list",
        }
        
        # Status values
        self.status_values = {
            "stock": "stock",
            "implementation": "implementation", 
            "production": "production",
            "obsolete": "obsolete",
            "active": ["stock", "implementation", "production"],
            "inactive": "obsolete"
        }
        
        # Business criticality values
        self.criticality_values = {
            "critical": "critical",
            "high": "high",
            "medium": "medium", 
            "low": "low"
        }
    
    async def process_query(self, query: str, limit: int = 100) -> str:
        """Process PC query"""
        intent = self._parse_query_intent(query)
        
        oql_query = self.build_oql_query(intent)
        output_fields = self.determine_output_fields(intent)
        
        operation = {
            "operation": "core/get",
            "class": self.class_name,
            "key": oql_query,
            "output_fields": output_fields,
            "limit": limit
        }
        
        result = await self.client.make_request(operation)
        return self._format_results(result, intent, query, oql_query)
    
    def _parse_query_intent(self, query: str) -> Dict[str, Any]:
        """Parse PC query intent"""
        query_lower = query.lower()
        
        intent = {
            "action": "list",
            "filters": [],
            "grouping": None,
            "fields": []
        }
        
        # Determine action
        if any(word in query_lower for word in ["count", "how many", "total"]):
            intent["action"] = "count"
        elif any(word in query_lower for word in ["group by", "breakdown", "summary"]):
            intent["action"] = "group"
            intent["grouping"] = self._detect_grouping(query_lower)
        
        intent["filters"] = self._extract_filters(query_lower)
        return intent
    
    def _detect_grouping(self, query_lower: str) -> Optional[str]:
        """Detect grouping field for PCs"""
        if "by status" in query_lower:
            return "status"
        elif "by type" in query_lower:
            return "type"
        elif "by organization" in query_lower or "by org" in query_lower:
            return "org_name"
        elif "by location" in query_lower:
            return "location_name"
        elif "by brand" in query_lower:
            return "brand_name"
        elif "by os" in query_lower or "by operating system" in query_lower:
            return "osfamily_name"
        elif "by criticality" in query_lower:
            return "business_criticity"
        elif "by user" in query_lower:
            return "user_friendlyname"
        elif "by owner" in query_lower or "by team" in query_lower:
            return "owner_friendlyname"
        return None
    
    def _extract_filters(self, query_lower: str) -> List[Dict[str, Any]]:
        """Extract PC-specific filters"""
        filters = []
        
        # Status filters
        for status_term, status_value in self.status_values.items():
            if status_term in query_lower:
                if isinstance(status_value, list):
                    filters.append({
                        "field": "status",
                        "operator": "IN",
                        "values": status_value,
                        "display_name": f"{status_term} status"
                    })
                else:
                    filters.append({
                        "field": "status",
                        "operator": "=",
                        "value": status_value,
                        "display_name": f"{status_term} status"
                    })
        
        # PC type filters
        if "desktop" in query_lower:
            filters.append({
                "field": "type",
                "operator": "=",
                "value": "desktop",
                "display_name": "desktop PCs"
            })
        elif "laptop" in query_lower:
            filters.append({
                "field": "type",
                "operator": "=",
                "value": "laptop", 
                "display_name": "laptop PCs"
            })
        
        # Criticality filters - DYNAMIC: Handle any combination of criticality values
        found_criticalities = []
        for crit_term, crit_value in self.criticality_values.items():
            if crit_term in query_lower:
                found_criticalities.append((crit_term, crit_value))
        
        if len(found_criticalities) == 1:
            # Single criticality
            crit_term, crit_value = found_criticalities[0]
            filters.append({
                "field": "business_criticity",
                "operator": "=",
                "value": crit_value,
                "display_name": f"{crit_term} criticality"
            })
        elif len(found_criticalities) > 1:
            # Multiple criticalities - use IN operator for OR logic
            unique_values = list(set([crit_value for _, crit_value in found_criticalities]))
            unique_terms = list(set([crit_term for crit_term, _ in found_criticalities]))
            
            if len(unique_values) == 1:
                # Multiple terms mapping to same criticality value
                filters.append({
                    "field": "business_criticity",
                    "operator": "=",
                    "value": unique_values[0],
                    "display_name": f"{'/'.join(unique_terms)} criticality"
                })
            else:
                # Multiple different criticalities - support any combination
                filters.append({
                    "field": "business_criticity",
                    "operator": "IN",
                    "values": unique_values,
                    "display_name": f"{'/'.join(unique_terms)} criticality"
                })
        
        # Organization filters
        org_match = re.search(r'organization ["\']([^"\']+)["\']', query_lower)
        if org_match:
            org_name = org_match.group(1)
            filters.append({
                "field": "org_name",
                "operator": "LIKE",
                "value": f"%{org_name}%",
                "display_name": f"organization contains '{org_name}'"
            })
        
        # Location filters
        if "location" in query_lower:
            location_match = re.search(r'location ["\']([^"\']+)["\']', query_lower)
            if location_match:
                location_name = location_match.group(1)
                filters.append({
                    "field": "location_name",
                    "operator": "LIKE",
                    "value": f"%{location_name}%",
                    "display_name": f"location contains '{location_name}'"
                })
        
        # User assignment filters (who uses the PC)
        if "user" in query_lower:
            user_match = re.search(r'user ["\']([^"\']+)["\']', query_lower)
            if user_match:
                user_name = user_match.group(1)
                filters.append({
                    "field": "user_friendlyname",
                    "operator": "LIKE",
                    "value": f"%{user_name}%",
                    "display_name": f"user contains '{user_name}'"
                })
        
        # Owner/Team filters (which team owns the PC)
        if "owner" in query_lower or "team" in query_lower:
            owner_match = re.search(r'(?:owner|team) ["\']([^"\']+)["\']', query_lower)
            if owner_match:
                owner_name = owner_match.group(1)
                filters.append({
                    "field": "owner_friendlyname",
                    "operator": "LIKE",
                    "value": f"%{owner_name}%",
                    "display_name": f"owner team contains '{owner_name}'"
                })
        
        # OS filters
        if "windows" in query_lower:
            filters.append({
                "field": "osfamily_name",
                "operator": "LIKE",
                "value": "%Windows%",
                "display_name": "Windows OS"
            })
        elif "linux" in query_lower:
            filters.append({
                "field": "osfamily_name",
                "operator": "LIKE",
                "value": "%Linux%",
                "display_name": "Linux OS"
            })
        elif "mac" in query_lower:
            filters.append({
                "field": "osfamily_name",
                "operator": "LIKE",
                "value": "%Mac%",
                "display_name": "Mac OS"
            })
        
        return filters
    
    def build_oql_query(self, intent: Dict[str, Any]) -> str:
        """Build OQL query for PCs"""
        return SmartQueryBuilder.build_oql_query(self.class_name, intent["filters"])
    
    def determine_output_fields(self, intent: Dict[str, Any]) -> str:
        """Determine output fields for PCs"""
        if intent["action"] == "count":
            return f"id,{intent['grouping']}" if intent["grouping"] else "id"
        return "*+"
    
    def _format_results(self, result: dict, intent: Dict[str, Any], query: str, oql_query: str) -> str:
        """Format PC results"""
        if result.get("code") != 0:
            return f"❌ **PC Query Error**: {result.get('message', 'Unknown error')}"
        
        objects = result.get("objects", {})
        message = result.get("message", "")
        total_count = _extract_count_from_message(message)
        
        output = f"**💻 PC Query Results**\n\n"
        output += f"**Query**: \"{query}\"\n"
        output += f"**OQL Used**: `{oql_query}`\n"
        
        if intent["filters"]:
            filter_descriptions = [f.get("display_name", "unknown filter") for f in intent["filters"]]
            output += f"**Filters Applied**: {', '.join(filter_descriptions)}\n"
        
        if total_count is not None:
            output += f"**Total Found**: {total_count}\n"
        output += f"**Returned**: {len(objects) if objects else 0}\n\n"
        
        if not objects:
            return output + "No PCs found matching your criteria."
        
        if intent["action"] == "count":
            return output + f"**Total PCs**: {total_count or len(objects)}"
        elif intent["action"] == "group":
            return output + SmartGroupingEngine.format_grouped_results(objects, intent["grouping"], self.class_name)
        else:
            return output + self._format_detailed_results(objects)
    
    def _format_detailed_results(self, objects: dict) -> str:
        """Format detailed PC results"""
        output = ""
        
        for i, (obj_key, obj_data) in enumerate(objects.items(), 1):
            if obj_data.get("code") == 0:
                fields = obj_data.get("fields", {})
                
                name = fields.get("name", obj_key)
                pc_type = fields.get("type", "Unknown")
                status = fields.get("status", "Unknown")
                
                output += f"{i}. **{name}** ({pc_type})\n"
                output += f"   Status: {status}\n"
                
                if fields.get("user_friendlyname"):
                    output += f"   👤 Assigned User: {fields['user_friendlyname']}\n"
                if fields.get("owner_friendlyname"):
                    output += f"   👥 Owner Team: {fields['owner_friendlyname']}\n"
                if fields.get("org_name"):
                    output += f"   🏢 Organization: {fields['org_name']}\n"
                if fields.get("location_name"):
                    output += f"   📍 Location: {fields['location_name']}\n"
                if fields.get("cpu"):
                    output += f"   🖥️ CPU: {fields['cpu']}\n"
                if fields.get("ram"):
                    output += f"   💾 RAM: {fields['ram']}\n"
                if fields.get("osfamily_name"):
                    os_display = fields['osfamily_name']
                    if fields.get("osversion_name"):
                        os_display += f" ({fields['osversion_name']})"
                    output += f"   💿 OS: {os_display}\n"
                if fields.get("oslicence_name"):
                    output += f"   📄 OS License: {fields['oslicence_name']}\n"
                if fields.get("business_criticity"):
                    crit_emoji = {"critical": "🔴", "high": "🟡", "medium": "🟢", "low": "⚪"}.get(fields["business_criticity"], "")
                    output += f"   📊 Criticality: {crit_emoji} {fields['business_criticity']}\n"
                if fields.get("serialnumber"):
                    output += f"   🔢 Serial: {fields['serialnumber']}\n"
                if fields.get("asset_number"):
                    output += f"   🏷️ Asset #: {fields['asset_number']}\n"
                
                output += "\n"
        
        return output


class ServerHandler(SmartHandlerBase):
    """Handler for Server queries"""
    
    def __init__(self, client: ITopClient):
        super().__init__(client, "Server")
        
        self.field_mappings = {
            # Core fields  
            "name": "name",
            "description": "description",
            "organization": "org_name",
            "status": "status",
            "business_criticality": "business_criticity",
            
            # Hardware and location
            "serial_number": "serialnumber", 
            "brand": "brand_name",
            "model": "model_name",
            "cpu": "cpu",
            "ram": "ram",
            "asset_number": "asset_number",
            
            # Datacenter placement
            "rack": "rack_name",
            "enclosure": "enclosure_name",
            "location": "location_name",
            "rack_units": "nb_u",
            
            # OS information
            "os_family": "osfamily_name",
            "os_version": "osversion_name", 
            "os_license": "oslicence_name",
            "os_comment": "ocs_oscomment",
            
            # Network
            "management_ip": "managementip",
            
            # Power connections
            "power_a": "powerA_name",
            "power_b": "powerB_name",
            
            # Security
            "confidentiality": "confidentiality",
            "integrity": "integrity",
            "availability": "availability",
            "cvss": "cvss",
            
            # Ownership and relationships
            "owner": "owner_friendlyname",  # Team that owns the server
            "custodians": "custodian_list",  # People responsible for the server
            "contingency": "contingency_friendlyname",  # Backup server
            
            # Related objects
            "contacts": "contacts_list",
            "softwares": "softwares_list",
            "tickets": "tickets_list",
            "logical_volumes": "logicalvolumes_list",
        }
    
    async def process_query(self, query: str, limit: int = 100) -> str:
        """Process server query"""
        intent = self._parse_query_intent(query)
        
        oql_query = self.build_oql_query(intent)
        output_fields = self.determine_output_fields(intent)
        
        operation = {
            "operation": "core/get",
            "class": self.class_name,
            "key": oql_query,
            "output_fields": output_fields,
            "limit": limit
        }
        
        result = await self.client.make_request(operation)
        return self._format_results(result, intent, query, oql_query)
    
    def _parse_query_intent(self, query: str) -> Dict[str, Any]:
        """Parse server query intent"""
        query_lower = query.lower()
        
        intent = {
            "action": "list",
            "filters": [],
            "grouping": None,
            "fields": [],
            "focus": "server"  # Default focus
        }
        
        # Detect if query is specifically about software/applications
        if any(word in query_lower for word in ["software", "application", "applications", "installed", "softwares"]):
            intent["focus"] = "software"
        
        if any(word in query_lower for word in ["count", "how many", "total"]):
            intent["action"] = "count"
        elif any(word in query_lower for word in ["group by", "breakdown", "summary"]):
            intent["action"] = "group"
            intent["grouping"] = self._detect_grouping(query_lower)
        
        intent["filters"] = self._extract_filters(query_lower)
        return intent
    
    def _detect_grouping(self, query_lower: str) -> Optional[str]:
        """Detect grouping for servers"""
        if "by status" in query_lower:
            return "status"
        elif "by organization" in query_lower:
            return "org_name"
        elif "by location" in query_lower:
            return "location_name"
        elif "by rack" in query_lower:
            return "rack_name"
        elif "by os" in query_lower:
            return "osfamily_name"
        elif "by criticality" in query_lower:
            return "business_criticity"
        elif "by owner" in query_lower or "by team" in query_lower:
            return "owner_friendlyname"
        elif "by brand" in query_lower:
            return "brand_name"
        return None
    
    def _extract_filters(self, query_lower: str) -> List[Dict[str, Any]]:
        """Extract server-specific filters"""
        filters = []
        
        # Status filters
        if "production" in query_lower:
            filters.append({
                "field": "status",
                "operator": "=",
                "value": "production",
                "display_name": "production servers"
            })
        elif "implementation" in query_lower:
            filters.append({
                "field": "status", 
                "operator": "=",
                "value": "implementation",
                "display_name": "implementation servers"
            })
        
        # Criticality filters
        if "critical" in query_lower:
            filters.append({
                "field": "business_criticity",
                "operator": "=",
                "value": "critical",
                "display_name": "critical servers"
            })
        
        # Owner/Team filters
        if "owner" in query_lower or "team" in query_lower:
            owner_match = re.search(r'(?:owner|team) ["\']([^"\']+)["\']', query_lower)
            if owner_match:
                owner_name = owner_match.group(1)
                filters.append({
                    "field": "owner_friendlyname",
                    "operator": "LIKE",
                    "value": f"%{owner_name}%",
                    "display_name": f"owner team contains '{owner_name}'"
                })
        
        # Location/Datacenter filters
        if "location" in query_lower:
            location_match = re.search(r'location ["\']([^"\']+)["\']', query_lower)
            if location_match:
                location_name = location_match.group(1)
                filters.append({
                    "field": "location_name",
                    "operator": "LIKE",
                    "value": f"%{location_name}%",
                    "display_name": f"location contains '{location_name}'"
                })
        
        # Rack filters
        if "rack" in query_lower:
            rack_match = re.search(r'rack ["\']([^"\']+)["\']', query_lower)
            if rack_match:
                rack_name = rack_match.group(1)
                filters.append({
                    "field": "rack_name",
                    "operator": "LIKE",
                    "value": f"%{rack_name}%",
                    "display_name": f"rack contains '{rack_name}'"
                })
        
        # OS filters
        if "windows" in query_lower:
            filters.append({
                "field": "osfamily_name",
                "operator": "LIKE",
                "value": "%Windows%",
                "display_name": "Windows servers"
            })
        elif "linux" in query_lower:
            filters.append({
                "field": "osfamily_name",
                "operator": "LIKE",
                "value": "%Linux%",
                "display_name": "Linux servers"
            })
        
        # Server name filters - extract server names from query (improved for multiple names and misspellings)
        import re
        
        # Look for multiple server name patterns in the query
        server_names = []
        
        # Pattern 1: "server Server2", "on Server2", etc.
        server_matches = re.findall(r'(?:server\s+|on\s+)?([A-Za-z0-9\-_]+\d+)\b', query_lower)
        server_names.extend(server_matches)
        
        # Pattern 2: Quoted server names "Server2", 'dm-aws-demo-mnet-01'
        quoted_matches = re.findall(r'["\']([A-Za-z0-9\-_]+)["\']', query_lower)
        server_names.extend(quoted_matches)
        
        # Pattern 3: Hyphenated names like dm-aws-demo-mnet-01
        hyphen_matches = re.findall(r'\b([a-z]+-[a-z]+-[a-z]+-[a-z]+-\d+)\b', query_lower)
        server_names.extend(hyphen_matches)
        
        # Remove duplicates and common words
        unique_server_names = []
        common_words = ["server", "servers", "on", "the", "a", "an", "all", "list", "find", "show", "get", "software", "applications", "installed"]
        
        for name in server_names:
            if name.lower() not in common_words and name not in unique_server_names:
                unique_server_names.append(name)
        
        # Add filters for found server names
        if unique_server_names:
            if len(unique_server_names) == 1:
                # Single server name
                filters.append({
                    "field": "name",
                    "operator": "LIKE",
                    "value": f"%{unique_server_names[0]}%",
                    "display_name": f"server name contains '{unique_server_names[0]}'"
                })
            else:
                # Multiple server names - use OR logic
                filters.append({
                    "field": "name",
                    "operator": "IN",
                    "value": [f"%{name}%" for name in unique_server_names],
                    "display_name": f"server name contains any of: {', '.join(unique_server_names)}"
                })
        
        return filters
    
    def build_oql_query(self, intent: Dict[str, Any]) -> str:
        """Build OQL query for servers"""
        return SmartQueryBuilder.build_oql_query(self.class_name, intent["filters"])
    
    def determine_output_fields(self, intent: Dict[str, Any]) -> str:
        """Determine output fields for servers"""
        if intent["action"] == "count":
            return f"id,{intent['grouping']}" if intent["grouping"] else "id"
        
        # Use *+ to get all fields including relationships - this works better than explicit field lists
        return "*+"
    
    def _format_results(self, result: dict, intent: Dict[str, Any], query: str, oql_query: str) -> str:
        """Format server results"""
        if result.get("code") != 0:
            return f"❌ **Server Query Error**: {result.get('message', 'Unknown error')}"
        
        objects = result.get("objects", {})
        message = result.get("message", "")
        total_count = _extract_count_from_message(message)
        
        output = f"**🖥️ Server Query Results**\n\n"
        output += f"**Query**: \"{query}\"\n"
        output += f"**OQL Used**: `{oql_query}`\n"
        
        if intent["filters"]:
            filter_descriptions = [f.get("display_name", "unknown filter") for f in intent["filters"]]
            output += f"**Filters Applied**: {', '.join(filter_descriptions)}\n"
        
        if total_count is not None:
            output += f"**Total Found**: {total_count}\n"
        output += f"**Returned**: {len(objects) if objects else 0}\n\n"
        
        if not objects:
            return output + "No servers found matching your criteria."
        
        if intent["action"] == "count":
            return output + f"**Total Servers**: {total_count or len(objects)}"
        elif intent["action"] == "group":
            return output + SmartGroupingEngine.format_grouped_results(objects, intent["grouping"], self.class_name)
        elif intent["focus"] == "software":
            return output + self._format_software_focused_results(objects)
        else:
            return output + self._format_detailed_results(objects)
    
    def _format_detailed_results(self, objects: dict) -> str:
        """Format detailed server results"""
        output = ""
        
        for i, (obj_key, obj_data) in enumerate(objects.items(), 1):
            if obj_data.get("code") == 0:
                fields = obj_data.get("fields", {})
                
                name = fields.get("name", obj_key)
                status = fields.get("status", "Unknown")
                
                output += f"{i}. **{name}**\n"
                output += f"   Status: {status}\n"
                
                if fields.get("owner_friendlyname"):
                    output += f"   👥 Owner Team: {fields['owner_friendlyname']}\n"
                if fields.get("org_name"):
                    output += f"   🏢 Organization: {fields['org_name']}\n"
                if fields.get("location_name"):
                    output += f"   📍 Location: {fields['location_name']}\n"
                if fields.get("rack_name"):
                    rack_display = fields['rack_name']
                    if fields.get("nb_u"):
                        rack_display += f" ({fields['nb_u']}U)"
                    output += f"   🗄️ Rack: {rack_display}\n"
                if fields.get("enclosure_name"):
                    output += f"   📦 Enclosure: {fields['enclosure_name']}\n"
                if fields.get("managementip"):
                    output += f"   🌐 Management IP: {fields['managementip']}\n"
                if fields.get("cpu"):
                    output += f"   🖥️ CPU: {fields['cpu']}\n"
                if fields.get("ram"):
                    output += f"   💾 RAM: {fields['ram']}\n"
                if fields.get("osfamily_name"):
                    os_display = fields['osfamily_name']
                    if fields.get("osversion_name"):
                        os_display += f" ({fields['osversion_name']})"
                    output += f"   💿 OS: {os_display}\n"
                if fields.get("oslicence_name"):
                    output += f"   📄 OS License: {fields['oslicence_name']}\n"
                if fields.get("business_criticity"):
                    crit_emoji = {"critical": "🔴", "high": "🟡", "medium": "🟢", "low": "⚪"}.get(fields["business_criticity"], "")
                    output += f"   📊 Criticality: {crit_emoji} {fields['business_criticity']}\n"
                if fields.get("serialnumber"):
                    output += f"   🔢 Serial: {fields['serialnumber']}\n"
                if fields.get("powerA_name") or fields.get("powerB_name"):
                    power_info = []
                    if fields.get("powerA_name"):
                        power_info.append(f"A: {fields['powerA_name']}")
                    if fields.get("powerB_name"):
                        power_info.append(f"B: {fields['powerB_name']}")
                    output += f"   ⚡ Power: {', '.join(power_info)}\n"
                
                # Display software applications when available - Enhanced for complex structure
                if fields.get("softwares_list"):
                    softwares = fields["softwares_list"]
                    if isinstance(softwares, list) and softwares:
                        output += f"   💾 **Installed Software ({len(softwares)} applications)**:\n"
                        for j, software in enumerate(softwares[:10], 1):  # Limit to first 10 for readability
                            if isinstance(software, dict):
                                # Handle the complex nested structure from your example
                                software_display_name = (
                                    software.get("software_id_friendlyname") or  # "MySql 8"
                                    software.get("software_name") or             # "MySql" 
                                    software.get("friendlyname") or              # "Oracle Server2"
                                    software.get("name") or                      # "Oracle"
                                    "Unknown Software"
                                )
                                
                                # For database servers, show more context
                                if software.get("finalclass") == "DBServer":
                                    db_name = software.get("name", "Database")
                                    software_name = software.get("software_name", "Unknown DB")
                                    software_version = software.get("software_id_friendlyname", "")
                                    
                                    if software_version and software_version != software_name:
                                        output += f"      {j}. {software_name} ({software_version}) - {db_name}\n"
                                    else:
                                        output += f"      {j}. {software_name} - {db_name}\n"
                                else:
                                    output += f"      {j}. {software_display_name}\n"
                            else:
                                output += f"      {j}. {software}\n"
                        
                        if len(softwares) > 10:
                            output += f"      ... and {len(softwares) - 10} more applications\n"
                    elif isinstance(softwares, dict):
                        # Sometimes it might be a dict with object keys
                        software_count = len(softwares)
                        if software_count > 0:
                            output += f"   💾 **Installed Software ({software_count} applications)**:\n"
                            for j, (soft_key, soft_data) in enumerate(list(softwares.items())[:10], 1):
                                if isinstance(soft_data, dict) and soft_data.get("fields"):
                                    soft_fields = soft_data["fields"]
                                    software_name = (
                                        soft_fields.get("software_id_friendlyname") or 
                                        soft_fields.get("software_name") or 
                                        soft_fields.get("name") or 
                                        soft_key
                                    )
                                    output += f"      {j}. {software_name}\n"
                                else:
                                    output += f"      {j}. {soft_key}\n"
                            
                            if software_count > 10:
                                output += f"      ... and {software_count - 10} more applications\n"
                
                output += "\n"
        
        return output
    
    def _format_software_focused_results(self, objects: dict) -> str:
        """Format results with focus on software applications"""
        output = ""
        
        for i, (obj_key, obj_data) in enumerate(objects.items(), 1):
            if obj_data.get("code") == 0:
                fields = obj_data.get("fields", {})
                
                name = fields.get("name", obj_key)
                status = fields.get("status", "Unknown")
                
                output += f"{i}. **{name}** ({status})\n"
                
                # Show basic server info
                if fields.get("owner_friendlyname"):
                    output += f"   👥 Owner: {fields['owner_friendlyname']}\n"
                if fields.get("osfamily_name"):
                    os_display = fields['osfamily_name']
                    if fields.get("osversion_name"):
                        os_display += f" ({fields['osversion_name']})"
                    output += f"   💿 OS: {os_display}\n"
                
                # Focus on software list - Enhanced to handle complex nested structure
                if fields.get("softwares_list"):
                    softwares = fields["softwares_list"]
                    
                    if isinstance(softwares, list) and softwares:
                        output += f"\n   💾 **Installed Software ({len(softwares)} applications)**:\n"
                        
                        for j, software in enumerate(softwares, 1):
                            if isinstance(software, dict):
                                # Handle complex nested structure - the software data structure you showed
                                software_display_name = (
                                    software.get("software_id_friendlyname") or  # "MySql 8"
                                    software.get("software_name") or             # "MySql" 
                                    software.get("friendlyname") or              # "Oracle Server2"
                                    software.get("name") or                      # "Oracle"
                                    "Unknown Software"
                                )
                                
                                # Some software items are actually software instances with detailed info
                                if software.get("finalclass") == "DBServer":
                                    # This is a database server software instance
                                    db_name = software.get("name", "Database")
                                    software_name = software.get("software_name", "Unknown DB")
                                    software_version = software.get("software_id_friendlyname", "")
                                    
                                    if software_version and software_version != software_name:
                                        output += f"      {j}. {software_name} ({software_version}) - {db_name}\n"
                                    else:
                                        output += f"      {j}. {software_name} - {db_name}\n"
                                else:
                                    # Standard software entry
                                    output += f"      {j}. {software_display_name}\n"
                                
                                # Show database schemas if available
                                if software.get("dbschema_list"):
                                    schemas = software["dbschema_list"]
                                    if isinstance(schemas, list) and schemas:
                                        schema_names = [schema.get("name", "Unknown") for schema in schemas[:3]]
                                        if len(schemas) > 3:
                                            schema_display = f"{', '.join(schema_names)} (+{len(schemas)-3} more)"
                                        else:
                                            schema_display = ', '.join(schema_names)
                                        output += f"        └─ Schemas: {schema_display}\n"
                            else:
                                # Simple string entry
                                output += f"      {j}. {software}\n"
                        
                    elif isinstance(softwares, dict):
                        # Handle dict structure (object keys)
                        software_count = len(softwares)
                        if software_count > 0:
                            output += f"\n   💾 **Installed Software ({software_count} applications)**:\n"
                            for j, (soft_key, soft_data) in enumerate(softwares.items(), 1):
                                if isinstance(soft_data, dict) and soft_data.get("fields"):
                                    soft_fields = soft_data["fields"]
                                    software_name = (
                                        soft_fields.get("software_id_friendlyname") or 
                                        soft_fields.get("software_name") or 
                                        soft_fields.get("name") or 
                                        soft_key
                                    )
                                    output += f"      {j}. {software_name}\n"
                                else:
                                    output += f"      {j}. {soft_key}\n"
                    else:
                        output += f"\n   ⚠️  **No software applications found or data not available**\n"
                else:
                    output += f"\n   ⚠️  **No software list available for this server**\n"
                
                output += "\n"
        
        return output


class VirtualMachineHandler(SmartHandlerBase):
    """Handler for Virtual Machine queries"""
    
    def __init__(self, client: ITopClient):
        super().__init__(client, "VirtualMachine")
        
        self.field_mappings = {
            "name": "name",
            "description": "description", 
            "organization": "org_name",
            "status": "status",
            "business_criticality": "business_criticity",
            
            # Virtual infrastructure
            "virtual_host": "virtualhost_name",
            
            # OS information
            "os_family": "osfamily_name",
            "os_version": "osversion_name",
            "os_license": "oslicence_name",
            
            # Resources
            "cpu": "cpu",
            "ram": "ram",
            "management_ip": "managementip",
            
            # Ownership and management
            "owner": "owner_friendlyname",  # Team that owns the VM
            "custodian": "custodian_friendlyname",  # Person responsible for the VM
            
            # Security
            "confidentiality": "confidentiality",
            "integrity": "integrity", 
            "availability": "availability",
            "cvss": "cvss",
            
            # Related objects
            "contacts": "contacts_list",
            "softwares": "softwares_list", 
            "tickets": "tickets_list",
        }
    
    async def process_query(self, query: str, limit: int = 100) -> str:
        """Process virtual machine query"""
        intent = self._parse_query_intent(query)
        
        oql_query = self.build_oql_query(intent)
        output_fields = self.determine_output_fields(intent)
        
        operation = {
            "operation": "core/get",
            "class": self.class_name,
            "key": oql_query,
            "output_fields": output_fields,
            "limit": limit
        }
        
        result = await self.client.make_request(operation)
        return self._format_results(result, intent, query, oql_query)
    
    def _parse_query_intent(self, query: str) -> Dict[str, Any]:
        """Parse VM query intent"""
        query_lower = query.lower()
        
        intent = {
            "action": "list",
            "filters": [],
            "grouping": None,
            "fields": []
        }
        
        if any(word in query_lower for word in ["count", "how many", "total"]):
            intent["action"] = "count"
        elif any(word in query_lower for word in ["group by", "breakdown", "summary"]):
            intent["action"] = "group"
            intent["grouping"] = self._detect_grouping(query_lower)
        
        intent["filters"] = self._extract_filters(query_lower)
        return intent
    
    def _detect_grouping(self, query_lower: str) -> Optional[str]:
        """Detect grouping for VMs"""
        if "by status" in query_lower:
            return "status"
        elif "by host" in query_lower or "by virtual host" in query_lower:
            return "virtualhost_name"
        elif "by organization" in query_lower:
            return "org_name"
        elif "by os" in query_lower:
            return "osfamily_name"
        elif "by owner" in query_lower or "by team" in query_lower:
            return "owner_friendlyname"
        elif "by custodian" in query_lower:
            return "custodian_friendlyname"
        return None
    
    def _extract_filters(self, query_lower: str) -> List[Dict[str, Any]]:
        """Extract VM-specific filters"""
        filters = []
        
        if "production" in query_lower:
            filters.append({
                "field": "status",
                "operator": "=",
                "value": "production",
                "display_name": "production VMs"
            })
        
        if "critical" in query_lower:
            filters.append({
                "field": "business_criticity",
                "operator": "=", 
                "value": "critical",
                "display_name": "critical VMs"
            })
        
        # Owner/Team filters
        if "owner" in query_lower or "team" in query_lower:
            owner_match = re.search(r'(?:owner|team) ["\']([^"\']+)["\']', query_lower)
            if owner_match:
                owner_name = owner_match.group(1)
                filters.append({
                    "field": "owner_friendlyname",
                    "operator": "LIKE",
                    "value": f"%{owner_name}%",
                    "display_name": f"owner team contains '{owner_name}'"
                })
        
        # Virtual host filters
        if "host" in query_lower:
            host_match = re.search(r'host ["\']([^"\']+)["\']', query_lower)
            if host_match:
                host_name = host_match.group(1)
                filters.append({
                    "field": "virtualhost_name",
                    "operator": "LIKE",
                    "value": f"%{host_name}%",
                    "display_name": f"virtual host contains '{host_name}'"
                })
        
        # OS filters
        if "windows" in query_lower:
            filters.append({
                "field": "osfamily_name",
                "operator": "LIKE",
                "value": "%Windows%",
                "display_name": "Windows VMs"
            })
        elif "linux" in query_lower:
            filters.append({
                "field": "osfamily_name",
                "operator": "LIKE",
                "value": "%Linux%",
                "display_name": "Linux VMs"
            })
        
        return filters
    
    def build_oql_query(self, intent: Dict[str, Any]) -> str:
        """Build OQL query for VMs"""
        return SmartQueryBuilder.build_oql_query(self.class_name, intent["filters"])
    
    def determine_output_fields(self, intent: Dict[str, Any]) -> str:
        """Determine output fields for VMs"""
        if intent["action"] == "count":
            return f"id,{intent['grouping']}" if intent["grouping"] else "id"
        return "*+"
    
    def _format_results(self, result: dict, intent: Dict[str, Any], query: str, oql_query: str) -> str:
        """Format VM results"""
        if result.get("code") != 0:
            return f"❌ **Virtual Machine Query Error**: {result.get('message', 'Unknown error')}"
        
        objects = result.get("objects", {})
        message = result.get("message", "")
        total_count = _extract_count_from_message(message)
        
        output = f"**💻 Virtual Machine Query Results**\n\n"
        output += f"**Query**: \"{query}\"\n"
        output += f"**OQL Used**: `{oql_query}`\n"
        
        if intent["filters"]:
            filter_descriptions = [f.get("display_name", "unknown filter") for f in intent["filters"]]
            output += f"**Filters Applied**: {', '.join(filter_descriptions)}\n"
        
        if total_count is not None:
            output += f"**Total Found**: {total_count}\n"
        output += f"**Returned**: {len(objects) if objects else 0}\n\n"
        
        if not objects:
            return output + "No virtual machines found matching your criteria."
        
        if intent["action"] == "count":
            return output + f"**Total VMs**: {total_count or len(objects)}"
        elif intent["action"] == "group":
            return output + SmartGroupingEngine.format_grouped_results(objects, intent["grouping"], self.class_name)
        else:
            return output + self._format_detailed_results(objects)
    
    def _format_detailed_results(self, objects: dict) -> str:
        """Format detailed VM results"""
        output = ""
        
        for i, (obj_key, obj_data) in enumerate(objects.items(), 1):
            if obj_data.get("code") == 0:
                fields = obj_data.get("fields", {})
                
                name = fields.get("name", obj_key)
                status = fields.get("status", "Unknown")
                
                output += f"{i}. **{name}**\n"
                output += f"   Status: {status}\n"
                
                if fields.get("virtualhost_name"):
                    output += f"   🖥️ Virtual Host: {fields['virtualhost_name']}\n"
                if fields.get("owner_friendlyname"):
                    output += f"   👥 Owner Team: {fields['owner_friendlyname']}\n"
                if fields.get("custodian_friendlyname"):
                    output += f"   👤 Custodian: {fields['custodian_friendlyname']}\n"
                if fields.get("org_name"):
                    output += f"   🏢 Organization: {fields['org_name']}\n"
                if fields.get("managementip"):
                    output += f"   🌐 IP: {fields['managementip']}\n"
                if fields.get("cpu"):
                    output += f"   🖥️ CPU: {fields['cpu']}\n"
                if fields.get("ram"):
                    output += f"   💾 RAM: {fields['ram']}\n"
                if fields.get("osfamily_name"):
                    os_display = fields['osfamily_name']
                    if fields.get("osversion_name"):
                        os_display += f" ({fields['osversion_name']})"
                    output += f"   💿 OS: {os_display}\n"
                if fields.get("oslicence_name"):
                    output += f"   📄 OS License: {fields['oslicence_name']}\n"
                if fields.get("business_criticity"):
                    crit_emoji = {"critical": "🔴", "high": "🟡", "medium": "🟢", "low": "⚪"}.get(fields["business_criticity"], "")
                    output += f"   � Criticality: {crit_emoji} {fields['business_criticity']}\n"
                
                output += "\n"
        
        return output


class NetworkDeviceHandler(SmartHandlerBase):
    """Handler for Network Device queries"""
    
    def __init__(self, client: ITopClient):
        super().__init__(client, "NetworkDevice")
        
        self.field_mappings = {
            "name": "name",
            "description": "description",
            "organization": "org_name", 
            "status": "status",
            "business_criticality": "business_criticity",
            
            # Location and infrastructure
            "location": "location_name",
            "brand": "brand_name",
            "model": "model_name",
            "asset_number": "asset_number",
            "serial_number": "serialnumber",
            
            # Network specific
            "network_type": "networkdevicetype_name",
            "ios_version": "iosversion_name",
            "management_ip": "managementip",
            "ram": "ram",
            
            # Datacenter placement
            "rack": "rack_name",
            "enclosure": "enclosure_name",
            "rack_units": "nb_u",
            
            # Power connections
            "power_a": "powerA_name",
            "power_b": "powerB_name",
            
            # Security ratings (missing from original)
            "confidentiality": "confidentiality",
            "integrity": "integrity",
            "availability": "availability",
            "score": "score",
            "cvss": "cvss",
            
            # Ownership and relationships (corrected field names)
            "owner": "owner_friendlyname",  # Team that owns the device
            "custodians": "custodian_list",  # People responsible for the device
            "contingency": "contingency_friendlyname",  # Backup device
            
            # Related objects
            "contacts": "contacts_list",
            "connected_devices": "connectablecis_list",
            "softwares": "softwares_list",
            "tickets": "tickets_list",
            "documents": "documents_list",
            "services": "services_list",
            "fiber_interfaces": "fiberinterfacelist_list",
            "sans": "san_list",
            "physical_interfaces": "physicalinterface_list",
            
            # Dates
            "purchase_date": "purchase_date",
            "warranty_end": "end_of_warranty",
            "move_to_production": "move2production",
        }
    
    async def process_query(self, query: str, limit: int = 100) -> str:
        """Process network device query"""
        intent = self._parse_query_intent(query)
        
        oql_query = self.build_oql_query(intent)
        output_fields = self.determine_output_fields(intent)
        
        operation = {
            "operation": "core/get",
            "class": self.class_name,
            "key": oql_query,
            "output_fields": output_fields,
            "limit": limit
        }
        
        result = await self.client.make_request(operation)
        return self._format_results(result, intent, query, oql_query)
    
    def _parse_query_intent(self, query: str) -> Dict[str, Any]:
        """Parse network device query intent"""
        query_lower = query.lower()
        
        intent = {
            "action": "list",
            "filters": [],
            "grouping": None,
            "fields": []
        }
        
        if any(word in query_lower for word in ["count", "how many", "total"]):
            intent["action"] = "count"
        elif any(word in query_lower for word in ["group by", "breakdown", "summary"]):
            intent["action"] = "group"
            intent["grouping"] = self._detect_grouping(query_lower)
        
        intent["filters"] = self._extract_filters(query_lower)
        return intent
    
    def _detect_grouping(self, query_lower: str) -> Optional[str]:
        """Detect grouping for network devices"""
        if "by type" in query_lower:
            return "networkdevicetype_name"
        elif "by status" in query_lower:
            return "status"
        elif "by location" in query_lower:
            return "location_name"
        elif "by organization" in query_lower:
            return "org_name"
        elif "by brand" in query_lower:
            return "brand_name"
        elif "by owner" in query_lower or "by team" in query_lower:
            return "owner_friendlyname"
        elif "by rack" in query_lower:
            return "rack_name"
        return None
    
    def _extract_filters(self, query_lower: str) -> List[Dict[str, Any]]:
        """Extract network device specific filters"""
        filters = []
        
        # Device type filters
        if "switch" in query_lower:
            filters.append({
                "field": "networkdevicetype_name",
                "operator": "LIKE",
                "value": "%switch%",
                "display_name": "switch devices"
            })
        elif "router" in query_lower:
            filters.append({
                "field": "networkdevicetype_name", 
                "operator": "LIKE",
                "value": "%router%",
                "display_name": "router devices"
            })
        elif "firewall" in query_lower:
            filters.append({
                "field": "networkdevicetype_name",
                "operator": "LIKE", 
                "value": "%firewall%",
                "display_name": "firewall devices"
            })
        
        # Status filters
        if "production" in query_lower:
            filters.append({
                "field": "status",
                "operator": "=",
                "value": "production",
                "display_name": "production devices"
            })
        
        # Owner/Team filters  
        if "owner" in query_lower or "team" in query_lower:
            owner_match = re.search(r'(?:owner|team) ["\']([^"\']+)["\']', query_lower)
            if owner_match:
                owner_name = owner_match.group(1)
                filters.append({
                    "field": "owner_friendlyname",
                    "operator": "LIKE",
                    "value": f"%{owner_name}%",
                    "display_name": f"owner team contains '{owner_name}'"
                })
        
        # Location filters
        if "location" in query_lower:
            location_match = re.search(r'location ["\']([^"\']+)["\']', query_lower)
            if location_match:
                location_name = location_match.group(1)
                filters.append({
                    "field": "location_name",
                    "operator": "LIKE",
                    "value": f"%{location_name}%",
                    "display_name": f"location contains '{location_name}'"
                })
        
        # Rack filters
        if "rack" in query_lower:
            rack_match = re.search(r'rack ["\']([^"\']+)["\']', query_lower)
            if rack_match:
                rack_name = rack_match.group(1)
                filters.append({
                    "field": "rack_name",
                    "operator": "LIKE",
                    "value": f"%{rack_name}%",
                    "display_name": f"rack contains '{rack_name}'"
                })
        
        # Security filters
        if "critical" in query_lower and "security" in query_lower:
            filters.append({
                "field": "business_criticity",
                "operator": "=",
                "value": "critical",
                "display_name": "critical network devices"
            })
        
        return filters
    
    def build_oql_query(self, intent: Dict[str, Any]) -> str:
        """Build OQL query for network devices"""
        return SmartQueryBuilder.build_oql_query(self.class_name, intent["filters"])
    
    def determine_output_fields(self, intent: Dict[str, Any]) -> str:
        """Determine output fields for network devices"""
        if intent["action"] == "count":
            return f"id,{intent['grouping']}" if intent["grouping"] else "id"
        return "*+"
    
    def _format_results(self, result: dict, intent: Dict[str, Any], query: str, oql_query: str) -> str:
        """Format network device results"""
        if result.get("code") != 0:
            return f"❌ **Network Device Query Error**: {result.get('message', 'Unknown error')}"
        
        objects = result.get("objects", {})
        message = result.get("message", "")
        total_count = _extract_count_from_message(message)
        
        output = f"**🌐 Network Device Query Results**\n\n"
        output += f"**Query**: \"{query}\"\n"
        output += f"**OQL Used**: `{oql_query}`\n"
        
        if intent["filters"]:
            filter_descriptions = [f.get("display_name", "unknown filter") for f in intent["filters"]]
            output += f"**Filters Applied**: {', '.join(filter_descriptions)}\n"
        
        if total_count is not None:
            output += f"**Total Found**: {total_count}\n"
        output += f"**Returned**: {len(objects) if objects else 0}\n\n"
        
        if not objects:
            return output + "No network devices found matching your criteria."
        
        if intent["action"] == "count":
            return output + f"**Total Network Devices**: {total_count or len(objects)}"
        elif intent["action"] == "group":
            return output + SmartGroupingEngine.format_grouped_results(objects, intent["grouping"], self.class_name)
        else:
            return output + self._format_detailed_results(objects)
    
    def _format_detailed_results(self, objects: dict) -> str:
        """Format detailed network device results"""
        output = ""
        
        for i, (obj_key, obj_data) in enumerate(objects.items(), 1):
            if obj_data.get("code") == 0:
                fields = obj_data.get("fields", {})
                
                name = fields.get("name", obj_key)
                device_type = fields.get("networkdevicetype_name", "Unknown")
                status = fields.get("status", "Unknown")
                
                output += f"{i}. **{name}** ({device_type})\n"
                output += f"   Status: {status}\n"
                
                if fields.get("owner_friendlyname"):
                    output += f"   👥 Owner Team: {fields['owner_friendlyname']}\n"
                if fields.get("org_name"):
                    output += f"   🏢 Organization: {fields['org_name']}\n"
                if fields.get("location_name"):
                    output += f"   📍 Location: {fields['location_name']}\n"
                if fields.get("managementip"):
                    output += f"   🌐 Management IP: {fields['managementip']}\n"
                if fields.get("brand_name"):
                    output += f"   🏭 Brand: {fields['brand_name']}\n"
                if fields.get("model_name"):
                    output += f"   📱 Model: {fields['model_name']}\n"
                if fields.get("iosversion_name"):
                    output += f"   💿 IOS Version: {fields['iosversion_name']}\n"
                if fields.get("rack_name"):
                    rack_display = fields['rack_name']
                    if fields.get("nb_u"):
                        rack_display += f" ({fields['nb_u']}U)"
                    output += f"   🗄️ Rack: {rack_display}\n"
                if fields.get("enclosure_name"):
                    output += f"   📦 Enclosure: {fields['enclosure_name']}\n"
                if fields.get("ram"):
                    output += f"   💾 RAM: {fields['ram']}\n"
                if fields.get("business_criticity"):
                    crit_emoji = {"critical": "🔴", "high": "🟡", "medium": "🟢", "low": "⚪"}.get(fields["business_criticity"], "")
                    output += f"   📊 Criticality: {crit_emoji} {fields['business_criticity']}\n"
                if fields.get("serialnumber"):
                    output += f"   🔢 Serial: {fields['serialnumber']}\n"
                if fields.get("asset_number"):
                    output += f"   🏷️ Asset #: {fields['asset_number']}\n"
                if fields.get("powerA_name") or fields.get("powerB_name"):
                    power_info = []
                    if fields.get("powerA_name"):
                        power_info.append(f"A: {fields['powerA_name']}")
                    if fields.get("powerB_name"):
                        power_info.append(f"B: {fields['powerB_name']}")
                    output += f"   ⚡ Power: {', '.join(power_info)}\n"
                
                output += "\n"
        
        return output


# =============================================================================
# People and Organization Handlers
# =============================================================================

class PersonHandler(SmartHandlerBase):
    """Handler for Person queries"""
    
    def __init__(self, client: ITopClient):
        super().__init__(client, "Person")
        
        self.field_mappings = {
            "name": "name",  # Last name
            "first_name": "first_name",
            "full_name": "friendlyname",
            "email": "email",
            "phone": "phone",
            "mobile": "mobile_phone",
            "status": "status",  # active/inactive
            "organization": "org_name",
            "function": "function",
            "employee_number": "employee_number",
            "location": "location_name",
            "manager": "manager_name",
            "business_criticality": "business_criticity",
            
            # Security ratings (from docs)
            "confidentiality": "confidentiality",
            "integrity": "integrity", 
            "availability": "availability",
            "score": "score",
            
            # Relationships
            "contingency": "contingency_friendlyname",  # Backup person
            "teams": "team_list",  # Teams this person belongs to
            "users": "user_list",  # User accounts for this person
            "tickets": "tickets_list",  # Tickets assigned to this person
            "cis": "cis_list",  # CIs this person is contact for
            
            # Additional fields
            "notify": "notify",  # Notification setting
            "picture": "picture",  # Profile picture
        }
        
        self.status_values = {
            "active": "active",
            "inactive": "inactive"
        }
    
    async def process_query(self, query: str, limit: int = 100) -> str:
        """Process person query"""
        intent = self._parse_query_intent(query)
        
        oql_query = self.build_oql_query(intent)
        output_fields = self.determine_output_fields(intent)
        
        operation = {
            "operation": "core/get",
            "class": self.class_name,
            "key": oql_query,
            "output_fields": output_fields,
            "limit": limit
        }
        
        result = await self.client.make_request(operation)
        return self._format_results(result, intent, query, oql_query)
    
    def _parse_query_intent(self, query: str) -> Dict[str, Any]:
        """Parse person query intent"""
        query_lower = query.lower()
        
        intent = {
            "action": "list",
            "filters": [],
            "grouping": None,
            "fields": []
        }
        
        if any(word in query_lower for word in ["count", "how many", "total"]):
            intent["action"] = "count"
        elif any(word in query_lower for word in ["group by", "breakdown", "summary"]):
            intent["action"] = "group"
            intent["grouping"] = self._detect_grouping(query_lower)
        
        intent["filters"] = self._extract_filters(query_lower)
        return intent
    
    def _detect_grouping(self, query_lower: str) -> Optional[str]:
        """Detect grouping for people"""
        if "by organization" in query_lower:
            return "org_name"
        elif "by location" in query_lower:
            return "location_name"
        elif "by function" in query_lower:
            return "function"
        elif "by status" in query_lower:
            return "status"
        return None
    
    def _extract_filters(self, query_lower: str) -> List[Dict[str, Any]]:
        """Extract person-specific filters"""
        filters = []
        
        # Status filters
        if "active" in query_lower and "people" in query_lower:
            filters.append({
                "field": "status",
                "operator": "=",
                "value": "active",
                "display_name": "active people"
            })
        elif "inactive" in query_lower:
            filters.append({
                "field": "status",
                "operator": "=",
                "value": "inactive", 
                "display_name": "inactive people"
            })
        
        # Organization filters
        org_match = re.search(r'organization ["\']([^"\']+)["\']', query_lower)
        if org_match:
            org_name = org_match.group(1)
            filters.append({
                "field": "org_name",
                "operator": "LIKE",
                "value": f"%{org_name}%",
                "display_name": f"organization contains '{org_name}'"
            })
        
        # Function/role filters
        if "manager" in query_lower and "function" in query_lower:
            filters.append({
                "field": "function",
                "operator": "LIKE",
                "value": "%manager%",
                "display_name": "managers"
            })
        
        return filters
    
    def build_oql_query(self, intent: Dict[str, Any]) -> str:
        """Build OQL query for people"""
        return SmartQueryBuilder.build_oql_query(self.class_name, intent["filters"])
    
    def determine_output_fields(self, intent: Dict[str, Any]) -> str:
        """Determine output fields for people"""
        if intent["action"] == "count":
            return f"id,{intent['grouping']}" if intent["grouping"] else "id"
        return "*+"
    
    def _format_results(self, result: dict, intent: Dict[str, Any], query: str, oql_query: str) -> str:
        """Format person results"""
        if result.get("code") != 0:
            return f"❌ **Person Query Error**: {result.get('message', 'Unknown error')}"
        
        objects = result.get("objects", {})
        message = result.get("message", "")
        total_count = _extract_count_from_message(message)
        
        output = f"**👤 Person Query Results**\n\n"
        output += f"**Query**: \"{query}\"\n"
        output += f"**OQL Used**: `{oql_query}`\n"
        
        if intent["filters"]:
            filter_descriptions = [f.get("display_name", "unknown filter") for f in intent["filters"]]
            output += f"**Filters Applied**: {', '.join(filter_descriptions)}\n"
        
        if total_count is not None:
            output += f"**Total Found**: {total_count}\n"
        output += f"**Returned**: {len(objects) if objects else 0}\n\n"
        
        if not objects:
            return output + "No people found matching your criteria."
        
        if intent["action"] == "count":
            return output + f"**Total People**: {total_count or len(objects)}"
        elif intent["action"] == "group":
            return output + SmartGroupingEngine.format_grouped_results(objects, intent["grouping"], self.class_name)
        else:
            return output + self._format_detailed_results(objects)
    
    def _format_detailed_results(self, objects: dict) -> str:
        """Format detailed person results"""
        output = ""
        
        for i, (obj_key, obj_data) in enumerate(objects.items(), 1):
            if obj_data.get("code") == 0:
                fields = obj_data.get("fields", {})
                
                first_name = fields.get("first_name", "")
                last_name = fields.get("name", obj_key)
                full_name = f"{first_name} {last_name}" if first_name else last_name
                status = fields.get("status", "Unknown")
                
                output += f"{i}. **{full_name}**\n"
                output += f"   Status: {status}\n"
                
                if fields.get("org_name"):
                    output += f"   🏢 Organization: {fields['org_name']}\n"
                if fields.get("function"):
                    output += f"   💼 Function: {fields['function']}\n"
                if fields.get("email"):
                    output += f"   📧 Email: {fields['email']}\n"
                if fields.get("phone"):
                    output += f"   📞 Phone: {fields['phone']}\n"
                if fields.get("mobile_phone"):
                    output += f"   📱 Mobile: {fields['mobile_phone']}\n"
                if fields.get("location_name"):
                    output += f"   📍 Location: {fields['location_name']}\n"
                if fields.get("manager_name"):
                    output += f"   👨‍💼 Manager: {fields['manager_name']}\n"
                if fields.get("employee_number"):
                    output += f"   🆔 Employee #: {fields['employee_number']}\n"
                
                output += "\n"
        
        return output


class TeamHandler(SmartHandlerBase):
    """Handler for Team queries"""
    
    def __init__(self, client: ITopClient):
        super().__init__(client, "Team")
        
        self.field_mappings = {
            "name": "name",
            "status": "status",  # active/inactive
            "organization": "org_name",
            "email": "email",
            "phone": "phone",
            "function": "function",
            
            # Team specific fields
            "members": "persons_list",  # Team members
            "tickets": "tickets_list",  # Tickets assigned to team
            "cis": "cis_list",  # CIs this team is contact for
            "notify": "notify",  # Notification setting
        }
    
    async def process_query(self, query: str, limit: int = 100) -> str:
        """Process team query"""
        intent = self._parse_query_intent(query)
        
        oql_query = self.build_oql_query(intent)
        output_fields = self.determine_output_fields(intent)
        
        operation = {
            "operation": "core/get",
            "class": self.class_name,
            "key": oql_query,
            "output_fields": output_fields,
            "limit": limit
        }
        
        result = await self.client.make_request(operation)
        return self._format_results(result, intent, query, oql_query)
    
    def _parse_query_intent(self, query: str) -> Dict[str, Any]:
        """Parse team query intent"""
        query_lower = query.lower()
        
        intent = {
            "action": "list",
            "filters": [],
            "grouping": None,
            "fields": []
        }
        
        if any(word in query_lower for word in ["count", "how many", "total"]):
            intent["action"] = "count"
        elif any(word in query_lower for word in ["group by", "breakdown", "summary"]):
            intent["action"] = "group"
            intent["grouping"] = self._detect_grouping(query_lower)
        
        intent["filters"] = self._extract_filters(query_lower)
        return intent
    
    def _detect_grouping(self, query_lower: str) -> Optional[str]:
        """Detect grouping for teams"""
        if "by organization" in query_lower:
            return "org_name"
        elif "by function" in query_lower:
            return "function"
        elif "by status" in query_lower:
            return "status"
        return None
    
    def _extract_filters(self, query_lower: str) -> List[Dict[str, Any]]:
        """Extract team-specific filters"""
        filters = []
        
        if "active" in query_lower and "team" in query_lower:
            filters.append({
                "field": "status",
                "operator": "=",
                "value": "active",
                "display_name": "active teams"
            })
        
        return filters
    
    def build_oql_query(self, intent: Dict[str, Any]) -> str:
        """Build OQL query for teams"""
        return SmartQueryBuilder.build_oql_query(self.class_name, intent["filters"])
    
    def determine_output_fields(self, intent: Dict[str, Any]) -> str:
        """Determine output fields for teams"""
        if intent["action"] == "count":
            return f"id,{intent['grouping']}" if intent["grouping"] else "id"
        return "*+"
    
    def _format_results(self, result: dict, intent: Dict[str, Any], query: str, oql_query: str) -> str:
        """Format team results"""
        if result.get("code") != 0:
            return f"❌ **Team Query Error**: {result.get('message', 'Unknown error')}"
        
        objects = result.get("objects", {})
        message = result.get("message", "")
        total_count = _extract_count_from_message(message)
        
        output = f"**👥 Team Query Results**\n\n"
        output += f"**Query**: \"{query}\"\n"
        output += f"**OQL Used**: `{oql_query}`\n"
        
        if intent["filters"]:
            filter_descriptions = [f.get("display_name", "unknown filter") for f in intent["filters"]]
            output += f"**Filters Applied**: {', '.join(filter_descriptions)}\n"
        
        if total_count is not None:
            output += f"**Total Found**: {total_count}\n"
        output += f"**Returned**: {len(objects) if objects else 0}\n\n"
        
        if not objects:
            return output + "No teams found matching your criteria."
        
        if intent["action"] == "count":
            return output + f"**Total Teams**: {total_count or len(objects)}"
        elif intent["action"] == "group":
            return output + SmartGroupingEngine.format_grouped_results(objects, intent["grouping"], self.class_name)
        else:
            return output + self._format_detailed_results(objects)
    
    def _format_detailed_results(self, objects: dict) -> str:
        """Format detailed team results"""
        output = ""
        
        for i, (obj_key, obj_data) in enumerate(objects.items(), 1):
            if obj_data.get("code") == 0:
                fields = obj_data.get("fields", {})
                
                name = fields.get("name", obj_key)
                status = fields.get("status", "Unknown")
                
                output += f"{i}. **{name}**\n"
                output += f"   Status: {status}\n"
                
                if fields.get("org_name"):
                    output += f"   🏢 Organization: {fields['org_name']}\n"
                if fields.get("function"):
                    output += f"   💼 Function: {fields['function']}\n"
                if fields.get("email"):
                    output += f"   📧 Email: {fields['email']}\n"
                if fields.get("phone"):
                    output += f"   📞 Phone: {fields['phone']}\n"
                
                output += "\n"
        
        return output


class OrganizationHandler(SmartHandlerBase):
    """Handler for Organization queries"""
    
    def __init__(self, client: ITopClient):
        super().__init__(client, "Organization")
        
        self.field_mappings = {
            "name": "name",
            "code": "code", 
            "status": "status",  # active/inactive
            "parent": "parent_name",
            "delivery_model": "deliverymodel_name",
        }
    
    async def process_query(self, query: str, limit: int = 100) -> str:
        """Process organization query"""
        intent = self._parse_query_intent(query)
        
        oql_query = self.build_oql_query(intent)
        output_fields = self.determine_output_fields(intent)
        
        operation = {
            "operation": "core/get",
            "class": self.class_name,
            "key": oql_query,
            "output_fields": output_fields,
            "limit": limit
        }
        
        result = await self.client.make_request(operation)
        return self._format_results(result, intent, query, oql_query)
    
    def _parse_query_intent(self, query: str) -> Dict[str, Any]:
        """Parse organization query intent"""
        query_lower = query.lower()
        
        intent = {
            "action": "list",
            "filters": [],
            "grouping": None,
            "fields": []
        }
        
        if any(word in query_lower for word in ["count", "how many", "total"]):
            intent["action"] = "count"
        elif any(word in query_lower for word in ["group by", "breakdown", "summary"]):
            intent["action"] = "group"
            intent["grouping"] = self._detect_grouping(query_lower)
        
        intent["filters"] = self._extract_filters(query_lower)
        return intent
    
    def _detect_grouping(self, query_lower: str) -> Optional[str]:
        """Detect grouping for organizations"""
        if "by status" in query_lower:
            return "status"
        elif "by parent" in query_lower:
            return "parent_name"
        elif "by delivery model" in query_lower:
            return "deliverymodel_name"
        return None
    
    def _extract_filters(self, query_lower: str) -> List[Dict[str, Any]]:
        """Extract organization-specific filters"""
        filters = []
        
        if "active" in query_lower and "organization" in query_lower:
            filters.append({
                "field": "status",
                "operator": "=",
                "value": "active",
                "display_name": "active organizations"
            })
        
        return filters
    
    def build_oql_query(self, intent: Dict[str, Any]) -> str:
        """Build OQL query for organizations"""
        return SmartQueryBuilder.build_oql_query(self.class_name, intent["filters"])
    
    def determine_output_fields(self, intent: Dict[str, Any]) -> str:
        """Determine output fields for organizations"""
        if intent["action"] == "count":
            return f"id,{intent['grouping']}" if intent["grouping"] else "id"
        return "*+"
    
    def _format_results(self, result: dict, intent: Dict[str, Any], query: str, oql_query: str) -> str:
        """Format organization results"""
        if result.get("code") != 0:
            return f"❌ **Organization Query Error**: {result.get('message', 'Unknown error')}"
        
        objects = result.get("objects", {})
        message = result.get("message", "")
        total_count = _extract_count_from_message(message)
        
        output = f"**🏢 Organization Query Results**\n\n"
        output += f"**Query**: \"{query}\"\n"
        output += f"**OQL Used**: `{oql_query}`\n"
        
        if intent["filters"]:
            filter_descriptions = [f.get("display_name", "unknown filter") for f in intent["filters"]]
            output += f"**Filters Applied**: {', '.join(filter_descriptions)}\n"
        
        if total_count is not None:
            output += f"**Total Found**: {total_count}\n"
        output += f"**Returned**: {len(objects) if objects else 0}\n\n"
        
        if not objects:
            return output + "No organizations found matching your criteria."
        
        if intent["action"] == "count":
            return output + f"**Total Organizations**: {total_count or len(objects)}"
        elif intent["action"] == "group":
            return output + SmartGroupingEngine.format_grouped_results(objects, intent["grouping"], self.class_name)
        else:
            return output + self._format_detailed_results(objects)
    
    def _format_detailed_results(self, objects: dict) -> str:
        """Format detailed organization results"""
        output = ""
        
        for i, (obj_key, obj_data) in enumerate(objects.items(), 1):
            if obj_data.get("code") == 0:
                fields = obj_data.get("fields", {})
                
                name = fields.get("name", obj_key)
                status = fields.get("status", "Unknown")
                
                output += f"{i}. **{name}**\n"
                output += f"   Status: {status}\n"
                
                if fields.get("code"):
                    output += f"   📋 Code: {fields['code']}\n"
                if fields.get("parent_name"):
                    output += f"   🏢 Parent: {fields['parent_name']}\n"
                if fields.get("deliverymodel_name"):
                    output += f"   📊 Delivery Model: {fields['deliverymodel_name']}\n"
                
                output += "\n"
        
        return output
# =============================================================================
# Main Smart Query Processor V2
# =============================================================================

# Conditionally register the tool if mcp is available
if mcp:
    @mcp.tool()
    async def smart_query_v2(
        query: str,
        force_class: Optional[str] = None,
        limit: int = 100
    ) -> str:
        """
        Smart iTop Query Processor V2 - Class-Specific Query Engine
        Features:
        - Automatically detects the iTop class from a natural language query
        - Uses specialized handlers for common classes (UserRequest, Ticket, Server, etc.)
        - Supports real-time schema discovery using *+ output fields
        - Maps user-friendly field names to iTop schema fields
        - Handles vague queries, SLA analysis, deadlines, grouping, and counts
        - Falls back to a generic handler for unsupported classes

        Args:
            query (str): The natural language query to process
            force_class (Optional[str]): Force a specific iTop class (overrides auto-detection)
            limit (int): Maximum number of results to return (default: 100)
        """
        return await smart_query_v2_impl(query, force_class, limit)

async def smart_query_v2_impl(
    query: str,
    force_class: Optional[str] = None,
    limit: int = 100
) -> str:
    """
    Smart iTop Query Processor V2 - Implementation
    """
    try:
        if limit < 1:
            limit = 1
        
        if force_class:
            class_name = force_class
            confidence = 1.0
        else:
            class_name, confidence, _ = smart_class_detection(query)

        client = get_itop_client()
        handler_map = {
            "UserRequest": UserRequestHandler,
            "Ticket": TicketHandler,
            "Change": ChangeHandler,
            "Incident": IncidentHandler,
            "Problem": ProblemHandler,
            "PC": PCHandler,
            "Server": ServerHandler,
            "VirtualMachine": VirtualMachineHandler,
            "NetworkDevice": NetworkDeviceHandler,
            "Person": PersonHandler,
            "Team": TeamHandler,
            "Organization": OrganizationHandler,
        }
        handler_cls = handler_map.get(class_name)
        if handler_cls is not None:
            handler = handler_cls(client)
            return await handler.process_query(query, limit)
        else:
            return await _generic_handler(query, class_name, client, limit)
            
    except Exception as e:
        return f"❌ **Smart Query V2 Error**: {str(e)}"
async def _generic_handler(query: str, class_name: str, client: ITopClient, limit: int) -> str:
    """Enhanced generic handler for classes not yet implemented"""
    query_lower = query.lower()
    
    # Handle comparison queries (vs, compared to, etc.)
    if any(comp_word in query_lower for comp_word in ["vs", "versus", "compared to", "comparison"]):
        return await _handle_generic_comparison(query, class_name, client, limit)
    
    # Handle grouping/breakdown queries
    if any(group_word in query_lower for group_word in ["organization wise", "organisation wise", "by organization", "by organisation", "breakdown", "group by"]):
        return await _handle_generic_grouping(query, class_name, client, limit)
    
    # Simple count or list query
    if any(word in query_lower for word in ["count", "how many"]):
        operation = {
            "operation": "core/get",
            "class": class_name,
            "key": f"SELECT {class_name}",
            "output_fields": "id",
            "limit": limit
        }
    else:
        operation = {
            "operation": "core/get",
            "class": class_name,
            "key": f"SELECT {class_name}",
            "output_fields": "*+",
            "limit": min(limit, 10)  # Limit for detailed view
        }
    
    result = await client.make_request(operation)
    
    if result.get("code") != 0:
        return f"❌ **{class_name} Query Error**: {result.get('message', 'Unknown error')}"
    
    objects = result.get("objects", {})
    message = result.get("message", "")
    total_count = _extract_count_from_message(message)
    
    output = f"**📋 {class_name} Query Results**\n\n"
    output += f"**Query**: \"{query}\"\n"
    oql_query = operation["key"]
    output += f"**OQL Used**: `{oql_query}`\n"
    output += f"**Note**: Using generic handler (specific handler not yet implemented)\n"
    
    if total_count is not None:
        output += f"**Total Found**: {total_count}\n"
    output += f"**Returned**: {len(objects) if objects else 0}\n\n"
    
    if not objects:
        return output + f"No {class_name} records found."
    
    # Enhanced listing with better field detection
    for i, (obj_key, obj_data) in enumerate(objects.items(), 1):
        if obj_data.get("code") == 0:
            fields = obj_data.get("fields", {})
            
            # Try to show useful fields with priority order
            name_fields = ["name", "friendlyname", "title", "ref", "id"]
            name_value = None
            for field in name_fields:
                if field in fields and fields[field]:
                    name_value = fields[field]
                    break
            
            if not name_value:
                name_value = "Unknown"
            
            output += f"{i}. **{name_value}**\n"
            
            # Show most relevant fields based on class type
            interesting_fields = _get_interesting_fields_for_class(class_name)
            for field in interesting_fields:
                if field in fields and fields[field] and field not in name_fields:
                    display_name = field.replace("_", " ").title()
                    output += f"   {display_name}: {fields[field]}\n"
            output += "\n"
    
    return output

async def _handle_generic_comparison(query: str, class_name: str, client: ITopClient, limit: int) -> str:
    """Handle comparison queries for generic classes"""
    return f"**⚠️ Enhanced Comparison Handler Needed**\n\n" \
           f"The query \"{query}\" appears to be a comparison query for {class_name} class.\n" \
           f"This requires a specialized handler that can:\n" \
           f"- Parse comparison criteria\n" \
           f"- Execute multiple queries\n" \
           f"- Present side-by-side results\n\n" \
           f"Please implement a specific handler for {class_name} class to support this functionality."

async def _handle_generic_grouping(query: str, class_name: str, client: ITopClient, limit: int) -> str:
    """Handle grouping queries for generic classes"""
    
    # Try to detect grouping field
    grouping_field = None
    if "organization" in query.lower() or "organisation" in query.lower():
        grouping_field = "org_name"
    elif "status" in query.lower():
        grouping_field = "status"
    elif "location" in query.lower():
        grouping_field = "location_name"
    
    if not grouping_field:
        return f"**⚠️ Grouping Field Detection Failed**\n\n" \
               f"Could not determine the grouping field for query: \"{query}\"\n" \
               f"Please implement a specific handler for {class_name} class."
    
    # Execute grouped query
    operation = {
        "operation": "core/get",
        "class": class_name,
        "key": f"SELECT {class_name}",
        "output_fields": f"id,{grouping_field}",
        "limit": limit
    }
    
    result = await client.make_request(operation)
    
    if result.get("code") != 0:
        return f"❌ **{class_name} Grouping Error**: {result.get('message', 'Unknown error')}"
    
    objects = result.get("objects", {})
    total_count = _extract_count_from_message(result.get("message", ""))
    
    # Group results
    groups = {}
    for obj_key, obj_data in objects.items():
        if obj_data.get("code") == 0:
            fields = obj_data.get("fields", {})
            group_value = fields.get(grouping_field, "Unknown")
            if group_value not in groups:
                groups[group_value] = 0
            groups[group_value] += 1
    
    output = f"**📊 {class_name} Grouped by {grouping_field.replace('_', ' ').title()}**\n\n"
    output += f"**Query**: \"{query}\"\n"
    output += f"**Total Found**: {total_count or len(objects)}\n\n"
    
    for group_name, count in sorted(groups.items()):
        output += f"**{group_name}**: {count} items\n"
    
    return output

def _get_interesting_fields_for_class(class_name: str) -> List[str]:
    """Return interesting fields to display for each class type"""
    common_fields = ["status", "org_name", "organization", "description"]
    
    class_specific = {
        "Organization": ["status", "code", "parent_name", "deliverymodel_name"],
        "Location": ["status", "org_name", "country", "city", "address"],
        "Person": ["status", "org_name", "email", "phone", "function"],
        "Team": ["status", "org_name", "email", "function"],
        "Contact": ["status", "org_name", "email", "phone"],
        "Application": ["status", "org_name", "business_criticity", "move2production"],
        "Service": ["status", "org_name", "business_criticity", "description"],
    }
    
    return class_specific.get(class_name, common_fields)
@mcp.tool()
async def list_operations() -> str:
    """List all available operations in the iTop REST API."""
    try:
        client = get_itop_client()
        operation_data = {"operation": "list_operations"}
        result = await client.make_request(operation_data)
        
        if result.get("code") != 0:
            return f"Error: {result.get('message', 'Unknown error')}"
        
        operations = result.get("operations", [])
        output = "Available iTop REST API operations:\n\n"
        
        for op in operations:
            output += f"• {op.get('verb', 'Unknown')}: {op.get('description', 'No description')}\n"
        
        return output
    except Exception as e:
        return f"Error listing operations: {str(e)}"
    
def main():
    """Main entry point for the MCP server"""
    if not all([ITOP_BASE_URL, ITOP_USER, ITOP_PASSWORD]):
        print("Error: Missing required environment variables:")
        print("  - ITOP_BASE_URL: URL to your iTop instance")
        print("  - ITOP_USER: iTop username")  
        print("  - ITOP_PASSWORD: iTop password")
        print("  - ITOP_VERSION: API version (optional, default: 1.4)")
        exit(1)
        
    mcp.run(host="0.0.0.0",transport="http")

if __name__ == "__main__":
    main()
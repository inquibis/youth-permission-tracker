"""
Response formatting utilities for voice output
Formats API data into natural voice-friendly text
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ResponseFormatter:
    """Formats API responses for natural voice output"""
    
    @staticmethod
    def format_date(date_string: str, include_time: bool = False) -> str:
        """
        Convert ISO date string to natural voice format
        
        Args:
            date_string: ISO format date string (e.g., "2026-12-15")
            include_time: Include time if available
            
        Returns:
            Natural language date string (e.g., "December 15th")
        """
        try:
            if "T" in date_string:
                # Parse datetime
                dt = datetime.fromisoformat(date_string.replace("Z", "+00:00"))
            else:
                # Parse date only
                dt = datetime.strptime(date_string, "%Y-%m-%d")
            
            # Format: "December 15th" or "December 15th at 2 PM"
            month = dt.strftime("%B")  # Full month name
            day = dt.day
            
            # Add ordinal suffix (st, nd, rd, th)
            if day in [1, 21, 31]:
                suffix = "st"
            elif day in [2, 22]:
                suffix = "nd"
            elif day in [3, 23]:
                suffix = "rd"
            else:
                suffix = "th"
            
            result = f"{month} {day}{suffix}"
            
            if include_time and "T" in date_string:
                time_str = dt.strftime("%I:%M %p").lstrip("0").replace(":00 ", " ")
                result += f" at {time_str}"
            
            return result
        except (ValueError, AttributeError) as e:
            logger.warning(f"Error formatting date '{date_string}': {e}")
            return date_string


    @staticmethod
    def format_time(time_string: str) -> str:
        """
        Convert time string to natural voice format
        
        Args:
            time_string: Time string (e.g., "14:00", "14:00:00", "2:00 PM")
            
        Returns:
            Natural language time (e.g., "2 PM", "2:30 PM")
        """
        try:
            # Try parsing 24-hour format
            if ":" in time_string:
                if len(time_string.split(":")[0]) == 2 and int(time_string.split(":")[0]) > 12:
                    dt = datetime.strptime(time_string[:5], "%H:%M")
                    return dt.strftime("%I:%M %p").lstrip("0")
            
            return time_string
        except (ValueError, AttributeError) as e:
            logger.warning(f"Error formatting time '{time_string}': {e}")
            return time_string


    @staticmethod
    def format_cost(cost_value) -> str:
        """
        Convert numeric cost to natural voice format
        
        Args:
            cost_value: Cost as float or int
            
        Returns:
            Natural language cost (e.g., "five dollars", "five dollars and fifty cents")
        """
        try:
            cost = float(cost_value)
            dollars = int(cost)
            cents = round((cost - dollars) * 100)
            
            # Simple mapping for common numbers
            dollar_words = {
                0: "zero", 1: "one", 2: "two", 3: "three", 4: "four",
                5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine",
                10: "ten", 15: "fifteen", 20: "twenty", 25: "twenty five",
                50: "fifty", 100: "one hundred"
            }
            
            dollar_str = dollar_words.get(dollars, str(dollars))
            dollar_text = "dollar" if dollars == 1 else "dollars"
            
            if cents > 0:
                cents_str = dollar_words.get(cents, str(cents))
                cents_text = "cent" if cents == 1 else "cents"
                return f"{dollar_str} {dollar_text} and {cents_str} {cents_text}"
            else:
                return f"{dollar_str} {dollar_text}"
        except (ValueError, TypeError) as e:
            logger.warning(f"Error formatting cost '{cost_value}': {e}")
            return f"${cost_value}"


    @staticmethod
    def format_activity_list(activities: List[Dict], max_items: int = 3) -> str:
        """
        Format a list of activities for voice output
        
        Args:
            activities: List of activity dictionaries
            max_items: Maximum number of activities to include
            
        Returns:
            Formatted activity list string
        """
        if not activities:
            return "You don't have any upcoming activities."
        
        activity_count = len(activities)
        displayed_count = min(max_items, activity_count)
        
        speech_text = f"You have {activity_count} upcoming activity"
        speech_text += "" if activity_count == 1 else "ies"
        
        if displayed_count > 0:
            speech_text += ". Here are the first "
            if displayed_count < activity_count:
                speech_text += f"{displayed_count}: "
            else:
                speech_text += "ones: "
            
            activity_lines = []
            for i, activity in enumerate(activities[:max_items], 1):
                activity_name = activity.get("name") or activity.get("activity_name", "Unknown")
                activity_date = activity.get("date") or activity.get("date_start", "")
                
                if activity_date:
                    formatted_date = ResponseFormatter.format_date(activity_date)
                    activity_lines.append(f"{i}) {activity_name} on {formatted_date}")
                else:
                    activity_lines.append(f"{i}) {activity_name}")
            
            speech_text += ". ".join(activity_lines) + "."
        
        if displayed_count < activity_count:
            speech_text += f" There are {activity_count - displayed_count} more. Would you like to hear about more, or get details on any of these?"
        else:
            speech_text += " Would you like details about any of these?"
        
        return speech_text


    @staticmethod
    def format_activity_details(activity: Dict) -> str:
        """
        Format full activity details for voice output
        
        Args:
            activity: Activity dictionary
            
        Returns:
            Formatted activity details string
        """
        name = activity.get("activity_name") or activity.get("name", "Unknown Activity")
        
        # Build details progressively
        details = [f"{name}"]
        
        # Date and time
        date_start = activity.get("date_start") or activity.get("date", "")
        date_end = activity.get("date_end") or ""
        start_time = activity.get("start_time", "")
        end_time = activity.get("end_time", "")
        
        if date_start:
            formatted_date = ResponseFormatter.format_date(date_start)
            
            if start_time and end_time:
                formatted_start = ResponseFormatter.format_time(start_time)
                formatted_end = ResponseFormatter.format_time(end_time)
                details.append(f"is on {formatted_date} from {formatted_start} to {formatted_end}")
            elif start_time:
                formatted_start = ResponseFormatter.format_time(start_time)
                details.append(f"is on {formatted_date} at {formatted_start}")
            else:
                details.append(f"is on {formatted_date}")
        
        # Location
        location = activity.get("location", "")
        if location and details[-1].endswith(name):
            # No date/time added yet, add location first
            details.append(f"in {location}")
        elif location:
            # Replace period with location info
            if details[-1].endswith("."):
                details[-1] = details[-1][:-1] + f" in {location}."
            else:
                details.append(f"in {location}")
        
        # Description
        description = activity.get("description", "")
        if description:
            # Truncate long descriptions for voice
            if len(description) > 200:
                description = description[:200] + "..."
            details.append(description)
        
        # Additional attributes
        is_overnight = activity.get("is_overnight", False)
        is_coed = activity.get("is_coed", False)
        requires_permission = activity.get("requires_permission", False)
        
        attributes = []
        if is_overnight:
            attributes.append("overnight")
        if is_coed:
            attributes.append("coed")
        
        if attributes:
            attr_str = " and ".join(attributes)
            details.append(f"It's a {attr_str} activity.")
        
        if requires_permission:
            details.append("This activity requires parental permission.")
        
        # Cost info
        total_cost = activity.get("total_cost")
        if total_cost and total_cost > 0:
            formatted_cost = ResponseFormatter.format_cost(total_cost)
            details.append(f"The cost is {formatted_cost}.")
        
        return " ".join(details)


    @staticmethod
    def format_permission_list(activities: List[Dict], max_items: int = 5) -> str:
        """
        Format list of activities needing permission
        
        Args:
            activities: List of activities requiring permission
            max_items: Maximum number of activities to show
            
        Returns:
            Formatted permission list string
        """
        if not activities:
            return "You don't have any activities that need permission approval right now."
        
        count = len(activities)
        displayed = min(max_items, count)
        
        speech_text = f"You have {count} activity"
        speech_text += "" if count == 1 else "ies"
        speech_text += " that need"
        speech_text += "" if count == 1 else "s"
        speech_text += " your permission approval. "
        
        if displayed > 0:
            speech_text += "Here "
            speech_text += "it is" if count == 1 else f"are the first {displayed}"
            speech_text += ": "
            
            activity_lines = []
            for i, activity in enumerate(activities[:max_items], 1):
                activity_name = activity.get("activity_name") or activity.get("name", "Unknown")
                activity_date = activity.get("date_start") or activity.get("date", "")
                
                if activity_date:
                    formatted_date = ResponseFormatter.format_date(activity_date)
                    activity_lines.append(f"{i}) {activity_name} on {formatted_date}")
                else:
                    activity_lines.append(f"{i}) {activity_name}")
            
            speech_text += ". ".join(activity_lines) + ". "
        
        if displayed < count:
            speech_text += f"There are {count - displayed} more. "
        
        speech_text += "Which activity would you like to approve?"
        
        return speech_text

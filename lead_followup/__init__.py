"""Automatische Follow-up-Mails für eingehende Leads."""

from lead_followup.schedule import process_due, schedule_followup

__all__ = ["schedule_followup", "process_due"]

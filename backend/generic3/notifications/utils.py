def generate_notification_message(sender_user= None , receiver_user = None , type = 'default' , **kwargs):
    if type == 'file_shared':
        # extract files name if provided
        names = kwargs.get('file_names' , [])
        title = f"{sender_user.get_full_name()} has shared a file(s) with you."
        message = f"{sender_user.get_full_name()} has shared the file(s) '{', '.join(names)}' with you. Please check your files section to access it."
        return title , message
    elif type == 'medication_reminder':
        medication_name = kwargs.get('medication_name' , 'your medication')
        title = "Medication Reminder"
        message = f"Time to take {medication_name}."
        return title , message
    elif type == 'activity_reminder':
        activity_name = kwargs.get('activity_name' , 'an activity')
        title = "Activity Reminder"
        message = f"Time to perform {activity_name}."
        return title , message
    else:
        return f"You have a new notification from {sender_user.get_full_name()}."
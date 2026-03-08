import base64
import mimetypes
import boto3
from users.models import Doctor, Patient
from fileshare.models import SharedFiles

def upload_file_to_s3_and_DB(files, clinic, patient , doctor):
    '''
    Uploads files to S3 and records metadata in the database.
    '''
    s3 = boto3.client('s3', region_name='il-central-1')

    uploaded_files = []
    for file in files:
        if not file:
            continue
        filename = file.name
        path = f"clinic/{clinic.id}/patient/{patient.id}/fileShare/{filename}" 
        
        # Properly detect content type
        content_type = getattr(file, "content_type", None)
        if not content_type or content_type == "application/octet-stream":
            guessed_type, _ = mimetypes.guess_type(filename)
            content_type = guessed_type or "application/octet-stream"
        
        print(f"Uploading file: {filename}, size: {file.size}, content_type: {content_type}")
        
        try:
            res = s3.put_object(
                Body=file.read(),  # Read the file content
                Bucket='generic3-bucket', 
                Key=path.lstrip('/'),
                ContentType=content_type,
                ContentDisposition=f'inline; filename="{filename}"'  # Include filename for better handling
            )
            if res['ResponseMetadata']['HTTPStatusCode'] == 200:
                patient = Patient.objects.get(user=patient.id)
                doctor = Doctor.objects.get(user=doctor.id)
                file_obj = SharedFiles(
                    file_name=filename,
                    size=file.size,
                    file_path=path,
                    patient=patient,
                    doctor=doctor,
                    clinic=clinic,
                )
                file_obj.save()
                uploaded_files.append({
                    "id": file_obj.id, 
                    "name": filename, 
                    "path": path, 
                    "size": file.size,
                    "content_type": content_type
                })
            else:
                return uploaded_files, f"Failed to upload {filename}"
        except Exception as e:
            return uploaded_files, f"Error uploading {filename}: {str(e)}"

    return uploaded_files, None

def view_file_from_s3(file_path , file_name=None):
    '''
    Retrieves a file from S3.
    '''
    s3 = boto3.client('s3', region_name='il-central-1')
    try:
        s3_response = s3.get_object(Bucket='generic3-bucket', Key=file_path)
        content = s3_response['Body'].read()
        content_type = s3_response.get('ContentType')
    except Exception as e:
        return None, None

    # Fallback to extension-based guessing for ANY generic type
    if not content_type or content_type in ('application/octet-stream', 'binary/octet-stream'):
        guessed, _ = mimetypes.guess_type(file_name)
        content_type = guessed or 'application/octet-stream'

    base64_data = base64.b64encode(content).decode('utf-8')
    return base64_data, content_type

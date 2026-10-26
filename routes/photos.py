# photo blueprint : blueprints lets flask grp photo-related endpoints separately from your authentication endpoints.(REFER TO AUTH.PY)
import traceback
from flask import request,jsonify,Blueprint
from flask_jwt_extended import(
    jwt_required,
    get_jwt_identity
)
from database import get_db_connection
# we import Blueprint from flask
from flask import Blueprint

photos_bp = Blueprint("photos",__name__)
# photo_bp-->holds our blueprint
# "photos"-->is the internal blueprint name
# __name__ helps flask find related resources related to this name.

# registering the blueprint in app.py[SUCCESS]
# Configure safe upload limits

# Add allowed image types
# Define them in our python set
ALLOWED_IMAGE_TYPE = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

MAX_IMAGE_SIZE = 10*1024*1024 

# Also, checking a file's declared MIME type is not enough on its own. Later,  inspect the actual image content so that someone cannot disguise an unrelated file as a JPEG just by changing its filename.

# We create the upload photo endpoint
@photos_bp.post("/upload")
@jwt_required()
def upload_photo():
    # we first validate and authorize that the user can access this endpoint
    user_id = get_jwt_identity()
    event_id = request.form.get("event_id", "").strip()

    if not event_id:
        return jsonify({
            "error":"An event ID is required"
        }),400

    conn=None

    try:
        conn = get_db_connection()
        # cursor = conn.cursor()

        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT cm.role, e.status
                FROM church_members AS cm
                JOIN events AS e
                    ON e.church_id = cm.church_id
                WHERE cm.user_id = %s
                    AND e.event_id = %s
                """,(user_id,
                     event_id))
            # if the person is found then store it
            result = cursor.fetchone()

        # if the user is not found
        if not result:
            return jsonify({"error":"Event not found or you do not have access."}),403

        # unpack whatever is in result and use it to make our upload feature more secure
        role,status = result

        # based on event_status
        if status != "PUBLISHED":
            return jsonify({"error":"Photos can only be uploaded to published events."}),403

        # based on roles
        if role not in ("ADMIN","ORGANIZER") :
            return jsonify({"error":"You do not have permission to upload photos."}),403

        return jsonify({"message":"Authorization successful. No photo uploaded yet."}),200
    except Exception as e:
        app_error = "Unable to process the upload request."
        return jsonify({"error":app_error}),500
        # traceback.print_exc()
        # return jsonify({"error":str(e)}),500
    finally:
        if conn is not None:
            conn.close()

        


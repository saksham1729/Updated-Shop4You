import cv2, os, uuid, numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from django.conf import settings
from mediapipe.framework.formats import landmark_pb2

def draw_landmarks_on_image(image, detection_result):
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    pose_landmarks_list = detection_result.pose_landmarks
    annotated_image = np.copy(rgb_image)

    for pose_landmarks in pose_landmarks_list:
        proto = landmark_pb2.NormalizedLandmarkList()
        proto.landmark.extend([
            landmark_pb2.NormalizedLandmark(x=l.x, y=l.y, z=l.z) for l in pose_landmarks
        ])
        mp.solutions.drawing_utils.draw_landmarks(
            annotated_image,
            proto,
            mp.solutions.pose.POSE_CONNECTIONS,
            mp.solutions.drawing_styles.get_default_pose_landmarks_style()
        )

    
    return annotated_image

def calculate_distance(p1, p2):
    return np.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)

def midpoint(p1, p2):
    return type(p1)(x=(p1.x + p2.x)/2, y=(p1.y + p2.y)/2)

def estimate_measurements(pose_landmarks, user_height_cm):
    lm = mp.solutions.pose.PoseLandmark
    landmarks = {key: pose_landmarks[key] for key in [
        lm.LEFT_SHOULDER, lm.RIGHT_SHOULDER, lm.LEFT_ELBOW,lm.RIGHT_ELBOW, lm.LEFT_WRIST,lm.RIGHT_WRIST,
        lm.LEFT_HIP, lm.RIGHT_HIP, lm.LEFT_KNEE, lm.LEFT_ANKLE,
        lm.RIGHT_KNEE, lm.RIGHT_ANKLE, lm.NOSE
    ]}
    crown = type(landmarks[lm.NOSE])(x=landmarks[lm.NOSE].x, y=landmarks[lm.NOSE].y )  # Slightly above the nose for crown
    avg_ankle = midpoint(landmarks[lm.LEFT_ANKLE], landmarks[lm.RIGHT_ANKLE])
    scale = user_height_cm / calculate_distance(landmarks[lm.NOSE], landmarks[lm.RIGHT_ANKLE])
    measurements = {
        "Shoulder Width (cm)": calculate_distance(landmarks[lm.LEFT_SHOULDER], landmarks[lm.RIGHT_SHOULDER]) * scale,
        "Arm Length (cm)": (calculate_distance(landmarks[lm.LEFT_SHOULDER], landmarks[lm.LEFT_ELBOW]) +
                            calculate_distance(landmarks[lm.LEFT_ELBOW], landmarks[lm.LEFT_WRIST])) * scale,
        "Torso Length (cm)": calculate_distance(landmarks[lm.LEFT_SHOULDER], landmarks[lm.LEFT_HIP]) * scale,
        "Waist Width (cm)": calculate_distance(landmarks[lm.LEFT_HIP], landmarks[lm.RIGHT_HIP]) * scale,
        "Chest Width (cm)": calculate_distance(midpoint(landmarks[lm.LEFT_SHOULDER] , (midpoint(landmarks[lm.LEFT_HIP],landmarks[lm.LEFT_SHOULDER]) ) ),(midpoint(landmarks[lm.RIGHT_SHOULDER] , (midpoint(landmarks[lm.RIGHT_HIP],landmarks[lm.RIGHT_SHOULDER] )) ))) * scale * 1.9,  # Approximate chest width
        "Hip Width (cm)": calculate_distance(landmarks[lm.LEFT_HIP], landmarks[lm.RIGHT_HIP]) * scale,
        "Inseam Length (cm)": ((calculate_distance(landmarks[lm.LEFT_HIP], landmarks[lm.LEFT_KNEE]) +
                                calculate_distance(landmarks[lm.LEFT_KNEE], landmarks[lm.LEFT_ANKLE]) +
                                calculate_distance(landmarks[lm.RIGHT_HIP], landmarks[lm.RIGHT_KNEE]) +
                                calculate_distance(landmarks[lm.RIGHT_KNEE], landmarks[lm.RIGHT_ANKLE])) / 2) * scale,
        "Full Body Height (cm)": user_height_cm
    }

    print("Shoulder width:", measurements["Shoulder Width (cm)"])
    print("Chest width:", measurements["Chest Width (cm)"])
    print("User height:", user_height_cm)
    print("Scale factor:", scale)
    print("Inseam Length:", measurements["Inseam Length (cm)"])
    print("Torso Length:", measurements["Torso Length (cm)"])
    print("Arm Length:", measurements["Arm Length (cm)"])
    print("Waist Width:", measurements["Waist Width (cm)"])
    print("Hip Width:", measurements["Hip Width (cm)"])

    
    return measurements

def recommend_size(measurements):
    shoulder = measurements["Shoulder Width (cm)"]
    # Approximate shoulder width based on shoulder landmarks
    # Assuming shoulder width is roughly half the shoulder circumference    

    # Approximate circumference based on chest width
    chest = measurements["Chest Width (cm)"]
    # Assuming chest width is roughly half the chest circumference
    # Adjusting to approximate chest circumference from width
    # Adjusting to approximate chest circumference from width
    # Size recommendation logic based on shoulder and chest measurements
    if shoulder < 35 or chest < 85:
        return "XS"
    elif shoulder < 40 or chest < 90:
        return "S"
    elif shoulder < 45 or chest < 100:
        return "M"
    elif shoulder < 50 or chest < 110:
        return "L"
    else:
        return "XL"
    
def recommend_size_pants(measurements):
    inseam = measurements.get("Inseam Length (cm)", 0)
    waist = measurements.get("Waist Width (cm)", 0)

    if waist < 70 or inseam < 75:
        return "28"
    elif waist < 75 or inseam < 80:
        return "30"
    elif waist < 80 or inseam < 85:
        return "32"
    elif waist < 85 or inseam < 90:
        return "34"
    else:
        return "36"



def process_image_and_recommend_size(image_file, user_height_cm):
    temp_path = os.path.join(settings.MEDIA_ROOT, f"uploads/{uuid.uuid4()}.jpg")
    os.makedirs(os.path.dirname(temp_path), exist_ok=True)
    with open(temp_path, 'wb+') as f:
        for chunk in image_file.chunks():
            f.write(chunk)
    
    original_image_url = os.path.join(settings.MEDIA_URL, f"uploads/{os.path.basename(temp_path)}")
    mp_image = mp.Image.create_from_file(temp_path)
    model_path = os.path.join(settings.BASE_DIR, 'app', 'static', 'app', 'models', 'pose_landmarker_full.task')
    base_options = python.BaseOptions(model_asset_path=model_path)

    options = vision.PoseLandmarkerOptions(base_options=base_options, output_segmentation_masks=True)
    detector = vision.PoseLandmarker.create_from_options(options)
    detection_result = detector.detect(mp_image)
    pose_landmarks = detection_result.pose_landmarks[0]
    measurements = estimate_measurements(pose_landmarks, user_height_cm)
    recommended_size = recommend_size(measurements)
    pants_size = recommend_size_pants(measurements)

    annotated_image = draw_landmarks_on_image(mp_image.numpy_view(), detection_result)
    annotated_path = os.path.join(settings.MEDIA_ROOT, f"annotated/{uuid.uuid4()}.jpg")
    os.makedirs(os.path.dirname(annotated_path), exist_ok=True)
    cv2.imwrite(annotated_path, cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR))
    annotated_url = os.path.join(settings.MEDIA_URL, f"annotated/{os.path.basename(annotated_path)}")
    
    print("User height:", user_height_cm)
    print("Pose landmarks detected:", len(detection_result.pose_landmarks))
    print("Recommended size:", recommended_size)
    return recommended_size,original_image_url , annotated_url, pants_size

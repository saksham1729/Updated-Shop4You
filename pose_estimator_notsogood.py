import cv2, os, uuid, numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from django.conf import settings
from mediapipe.framework.formats import landmark_pb2
from .mesh_generator import generate_mesh_from_image, load_and_scale_mesh, extract_mesh_measurements
import os
from app.utils.keypoints_generator import generate_keypoints_json
from mediapipe.framework.formats import landmark_pb2
from mediapipe.python.solutions.pose import PoseLandmark as lm

import json
from app.utils.keypoints_generator import generate_keypoints_json



def draw_landmarks_on_image(image, detection_result):
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    pose_landmarks_list = detection_result.pose_world_landmarks
    annotated_image = np.copy(rgb_image)

    print(f"Detected {len(pose_landmarks_list)} pose landmarks")

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




def estimate_measurements_world(results, user_height_cm):
    
    def landmark_to_array(lm_obj):
        return np.array([lm_obj.x, lm_obj.y, lm_obj.z])

    def distance(a, b):
        return np.linalg.norm(np.array(a) - np.array(b))

    def midpoint(a, b):
        return (np.array(a) + np.array(b)) / 2
    


    print(f"[Debug] pose_world_landmarks type: {type(results.pose_world_landmarks)}")
    print(f"[Debug] First item type: {type(results.pose_world_landmarks[0])}")
    print(f"[Debug] pose_world_landmarks raw: {results.pose_world_landmarks}")


    if not results.pose_world_landmarks:
            raise ValueError("No world landmarks detected.")


    landmarks = results.pose_world_landmarks[0]

    # Convert key landmarks to arrays
    left_shoulder = landmark_to_array(landmarks[lm.LEFT_SHOULDER])
    right_shoulder = landmark_to_array(landmarks[lm.RIGHT_SHOULDER])
    left_elbow = landmark_to_array(landmarks[lm.LEFT_ELBOW])
    right_elbow = landmark_to_array(landmarks[lm.RIGHT_ELBOW])
    left_wrist = landmark_to_array(landmarks[lm.LEFT_WRIST])
    right_wrist = landmark_to_array(landmarks[lm.RIGHT_WRIST])
    left_hip = landmark_to_array(landmarks[lm.LEFT_HIP])
    right_hip = landmark_to_array(landmarks[lm.RIGHT_HIP])
    left_knee = landmark_to_array(landmarks[lm.LEFT_KNEE])
    right_knee = landmark_to_array(landmarks[lm.RIGHT_KNEE])
    left_ankle = landmark_to_array(landmarks[lm.LEFT_ANKLE])
    right_ankle = landmark_to_array(landmarks[lm.RIGHT_ANKLE])
    nose = landmark_to_array(landmarks[lm.NOSE])

    # Scaling factor
    height_m = distance(nose, right_ankle)
    scale = user_height_cm / (height_m * 100)

    # Shoulder width
    shoulder_width = distance(left_shoulder, right_shoulder) * 100 * scale

    # Chest circumference
    left_upper_arm_vec = left_elbow - left_shoulder
    right_upper_arm_vec = right_elbow - right_shoulder
    arm_scale = 0.25
    left_chest_edge = left_shoulder + arm_scale * left_upper_arm_vec
    right_chest_edge = right_shoulder + arm_scale * right_upper_arm_vec
    chest_width = distance(left_chest_edge, right_chest_edge) * 100 * scale
    chest_center = midpoint(left_chest_edge, right_chest_edge)
    back_center = midpoint(left_hip, right_hip)
    chest_depth = abs(chest_center[2] - back_center[2]) * 100 * scale
    a, b = chest_width / 2, chest_depth / 2
    chest_circumference = np.pi * (3*(a + b) - np.sqrt((3*a + b)*(a + 3*b)))

    # Waist width
    waist_ratio = 0.42
    left_waist = left_shoulder * (1 - waist_ratio) + left_hip * waist_ratio
    right_waist = right_shoulder * (1 - waist_ratio) + right_hip * waist_ratio
    waist_width = distance(left_waist, right_waist) * 100 * scale

    # Hip width with projection
    spine_mid = midpoint(left_hip, right_hip)
    def project_hip_outward(hip, spine_mid, scale_factor=0.15):
        direction = hip - spine_mid
        return hip + scale_factor * direction

    left_hip_proj = project_hip_outward(left_hip, spine_mid)
    right_hip_proj = project_hip_outward(right_hip, spine_mid)
    projected_hip_width = distance(left_hip_proj[:2], right_hip_proj[:2]) * 100 * scale
    z_offset = abs(left_hip[2] - right_hip[2]) * 100 * scale
    corrected_hip_width = np.sqrt(projected_hip_width**2 + z_offset**2)

    # Fallback logic
    lower_bound = shoulder_width * 0.7
    upper_bound = shoulder_width * 1.3
    hip_width = corrected_hip_width if lower_bound <= corrected_hip_width <= upper_bound else shoulder_width * 0.95

    # Inseam
    def vertical_inseam(hip_center, ankle):
        dy = abs(hip_center[1] - ankle[1])
        dz = abs(hip_center[2] - ankle[2])
        return np.sqrt(dy**2 + dz**2) * 100 * scale

    left_inseam = vertical_inseam(spine_mid, left_ankle)
    right_inseam = vertical_inseam(spine_mid, right_ankle)
    inseam = min((left_inseam + right_inseam) / 2, user_height_cm * 0.52)

    return {
        'Shoulder Width (cm)': shoulder_width,
        'Chest Circumference (cm)': chest_circumference,
        'Waist Width (cm)': waist_width,
        'Hip Width (cm)': hip_width,
        'Inseam Length (cm)': inseam,
        'Full Body Height (cm)': user_height_cm
    }



def compare_measurements(pose_measurements, mesh_measurements):
    comparison = {}
    for key in pose_measurements:
        if key in mesh_measurements:
            comparison[key] = {
                "2D": pose_measurements[key],
                "3D": mesh_measurements[key],
                "Difference": abs(pose_measurements[key] - mesh_measurements[key])
            }
    return comparison

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
    

def run_icon_inference(image_path):
    import subprocess
    subprocess.run([
        "python", "-m", "apps.infer",
        "--img_path", image_path
    ], check=True)
    return "ICON/output/output.obj"




def process_image_and_recommend_size(image_file, user_height_cm, use_3d=False):
    # 🔹 Save uploaded image
    temp_path = os.path.join(settings.MEDIA_ROOT, f"uploads/{uuid.uuid4()}.jpg")
    os.makedirs(os.path.dirname(temp_path), exist_ok=True)
    with open(temp_path, 'wb+') as f:
        for chunk in image_file.chunks():
            f.write(chunk)

    original_image_url = os.path.join(settings.MEDIA_URL, f"uploads/{os.path.basename(temp_path)}")
    mp_image = mp.Image.create_from_file(temp_path)

    # 🔹 Load pose detection model
    model_path = os.path.join(settings.BASE_DIR, 'app', 'static', 'app', 'models', 'pose_landmarker_full.task')
    base_options = python.BaseOptions(model_asset_path=model_path)
    options = vision.PoseLandmarkerOptions(base_options=base_options, output_segmentation_masks=True)
    detector = vision.PoseLandmarker.create_from_options(options)

    # 🔹 Run pose detection
    detection_result = detector.detect(mp_image)
    if not detection_result.pose_landmarks:
        raise ValueError("No pose landmarks detected in the image.")

    pose_measurements = estimate_measurements_world(detection_result, user_height_cm)
    print(f"[Pose] Measurements: {pose_measurements}")
    

    # 🔹 Save keypoints JSON
    keypoint_path = temp_path.replace('.jpg', '_keypoints.json')
    if not os.path.exists(keypoint_path):
        try:
            generate_keypoints_json(temp_path, keypoint_path)
            print(f"[Keypoints] Saved to: {keypoint_path}")
        except Exception as e:
            print(f"[Keypoints] Generation failed: {e}")
            if use_3d:
                raise RuntimeError("Keypoint generation failed, cannot proceed with 3D mesh.")

    # 🔹 Optional 3D mesh processing
    mesh_url = None
    if use_3d:
        try:
            mesh_path = generate_mesh_from_image(temp_path, output_dir="media/meshes")
            mesh, scale_factor = load_and_scale_mesh(mesh_path, user_height_cm)
            mesh_measurements = extract_mesh_measurements(mesh, user_height_cm)
            comparison = compare_measurements(pose_measurements, mesh_measurements)
            final_measurements = mesh_measurements

            mesh_url = os.path.join(settings.MEDIA_URL, f"meshes/pifuhd_final/recon/{os.path.basename(mesh_path)}")
            print(f"[Mesh] Generated and saved to: {mesh_url}")
        except Exception as e:
            print(f"[Mesh] Generation failed: {e}")
            final_measurements = pose_measurements
    else:
        final_measurements = pose_measurements


    # 🔧 Ensure required keys exist before size recommendation
    required_keys = {
        "Shoulder Width (cm)": 0,
        "Chest Width (cm)": 0,
        "Hip Width (cm)": 0,
        "Full Body Height (cm)": user_height_cm
    }

    final_measurements["Chest Width (cm)"] = final_measurements.get("Chest Circumference (cm)", 0) / np.pi
    final_measurements["Hip Width (cm)"] = final_measurements.get("Hip Circumference (cm)", 0) / np.pi
    final_measurements["Inseam Length (cm)"] = final_measurements.get("Inseam Length (cm)", 0)
    final_measurements["Waist Width (cm)"] = final_measurements.get("Waist Width (cm)", 0)
    final_measurements["Full Body Height (cm)"] = final_measurements.get("Full Body Height (cm)", user_height_cm)
    final_measurements["Chest Circumference (cm)"] = final_measurements.get("Chest Circumference (cm)", 0)
    final_measurements["Hip Circumference (cm)"] = final_measurements.get("Hip Circumference (cm)", 0)
    final_measurements["Shoulder Width (cm)"] = final_measurements.get("Shoulder Width (cm)", 0)
    

    for key, default in required_keys.items():
        if key not in final_measurements:
            print(f"⚠️ Missing key '{key}', defaulting to {default}")
            final_measurements[key] = default


    # 🔹 Size recommendation
    recommended_size = recommend_size(final_measurements)
    pants_size = recommend_size_pants(final_measurements)

    # 🔹 Annotated image
    annotated_image = draw_landmarks_on_image(mp_image.numpy_view(), detection_result)
    annotated_path = os.path.join(settings.MEDIA_ROOT, f"annotated/{uuid.uuid4()}.jpg")
    os.makedirs(os.path.dirname(annotated_path), exist_ok=True)
    cv2.imwrite(annotated_path, cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR))
    annotated_url = os.path.join(settings.MEDIA_URL, f"annotated/{os.path.basename(annotated_path)}")

    # 🔹 Debug logs
    print("User height:", user_height_cm)
    print("Pose landmarks detected:", len(detection_result.pose_landmarks))
    print("Recommended size:", recommended_size)

    
    return (
    recommended_size,
    original_image_url,
    annotated_url,
    pants_size,
    mesh_url if use_3d else None
    )


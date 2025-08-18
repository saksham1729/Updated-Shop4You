import subprocess
import os
import trimesh
import sys
from django.conf import settings
import cv2
import shutil
import uuid


def generate_mesh_from_image(image_path, output_dir, user_height_cm=182.0):
    os.makedirs(output_dir, exist_ok=True)

    # 🔹 Create temp input folder
    temp_input_dir = os.path.join(settings.MEDIA_ROOT, "pifu_input", str(uuid.uuid4()))
    os.makedirs(temp_input_dir, exist_ok=True)

    # 🔹 Prepare filenames
    image_filename = os.path.basename(image_path)
    base_name = os.path.splitext(image_filename)[0]
    keypoint_path = image_path.replace(".jpg", "_keypoints.json")
    rect_path = image_path.replace(".jpg", "_rect.txt")

    # 🔹 Validate keypoints
    if not os.path.exists(keypoint_path):
        raise FileNotFoundError(f"Keypoints file missing: {keypoint_path}")

    # 🔹 Create dummy _rect.txt
    with open(rect_path, "w") as f:
        f.write("0 0 512 512")  # Dummy bounding box

    # 🔹 Copy files to temp input folder
    shutil.copy(image_path, os.path.join(temp_input_dir, image_filename))
    shutil.copy(keypoint_path, os.path.join(temp_input_dir, f"{base_name}_keypoints.json"))
    shutil.copy(rect_path, os.path.join(temp_input_dir, f"{base_name}_rect.txt"))

    # 🔹 Debug input folder contents
    print(" Input folder contents:")
    for f in os.listdir(temp_input_dir):
        print("  -", f)

    # 🔹 Run mesh generation
    python_exec = sys.executable
    result = subprocess.run([
        python_exec, "-m", "pifuhd.apps.simple_test",
        "-i", temp_input_dir,
        "-o", output_dir,
        "--use_rect"
    ], cwd=settings.BASE_DIR, capture_output=True, text=True)

    print("🔧 Mesh generation stdout:", result.stdout)
    print("❗ Mesh generation stderr:", result.stderr)

    if result.returncode != 0:
        raise RuntimeError(f"Mesh generation failed:\n{result.stderr}")

    # 🔹 Validate mesh output
    mesh_path = find_mesh_file(output_dir)

    # 🔹 Rename to recon.obj for consistency
    final_path = os.path.join(output_dir, "recon.obj")
    shutil.copy(mesh_path, final_path)
    return final_path
    
def find_mesh_file(output_dir):
    for root, dirs, files in os.walk(output_dir):
        for file in files:
            if file.endswith(".obj") and "result_" in file:
                return os.path.join(root, file)
    raise FileNotFoundError("Mesh file not found in output directory.")


def load_and_scale_mesh(mesh_path, user_height_cm):
    mesh_path = os.path.abspath(mesh_path)
    if not os.path.isfile(mesh_path):
        raise FileNotFoundError(f"Mesh file not found: {mesh_path}")

    mesh = trimesh.load(mesh_path, force='mesh')
    scale_factor = compute_scale_factor(mesh, user_height_cm)
    mesh.apply_scale(scale_factor)
    return mesh, scale_factor


def extract_mesh_measurements(mesh,user_height_cm):
    import numpy as np

    vertices = mesh.vertices
    y_coords = vertices[:, 1]
    x_coords = vertices[:, 0]

    y_min, y_max = np.min(y_coords), np.max(y_coords)
    mesh_height = y_max - y_min
    scale_factor = user_height_cm / mesh_height
    

    def horizontal_width_at(relative_height):
        target_y = y_max - relative_height * mesh_height
        band = 0.02 * mesh_height  # ±2% height band
        indices = np.where((y_coords > target_y - band) & (y_coords < target_y + band))[0]
        if len(indices) < 2:
            return 0
        width = np.max(x_coords[indices]) - np.min(x_coords[indices])
        return np.max(x_coords[indices]) - np.min(x_coords[indices])

    shoulder_width = horizontal_width_at(0.10)  # Top 10%
    chest_width = horizontal_width_at(0.25)     # ~25% down
    hip_width = horizontal_width_at(0.55)       # ~55% down

    print(f"🧍‍♂️ Mesh Shoulder Width: {shoulder_width:.2f} cm")
    print(f"🫁 Mesh Chest Width: {chest_width:.2f} cm")
    print(f"🩳 Mesh Hip Width: {hip_width:.2f} cm")
    print(f"📏 User Height: {user_height_cm:.2f} cm")
    print(f"📐 Scale Factor: {scale_factor:.2f}")

    measurements = {
        "Shoulder Width (cm)": round(shoulder_width, 2),
        "Chest Width (cm)": round(chest_width, 2),
        "Hip Width (cm)": round(hip_width, 2),
        "Full Body Height (cm)": round(user_height_cm, 2)
    }

    return measurements




def compute_scale_factor(mesh, user_height_cm):
    mesh_height = mesh.bounds[1][2] - mesh.bounds[0][2]
    if mesh_height == 0:
        raise ValueError("Mesh height is zero — cannot scale.")
    return user_height_cm / mesh_height
def compare_measurements(pose_measurements, mesh_measurements):
    comparison = {}
    for key in pose_measurements:
        if key in mesh_measurements:
            comparison[key] = {
                "Pose": pose_measurements[key],
                "Mesh": mesh_measurements[key],
                "Difference (cm)": round(mesh_measurements[key] - pose_measurements[key], 2)
            }
        else:
            comparison[key] = {
                "Pose": pose_measurements[key],
                "Mesh": None,
                "Difference (cm)": None
            }
    return comparison






def save_mesh_with_color(save_path, verts, faces, image_tensor, calib_tensor, net, data):
    try:
        # 🔹 Ensure save directory exists
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        # 🔹 Project vertices to image space
        verts_tensor = torch.Tensor(verts).unsqueeze(0)
        xyz_tensor = net.projection(verts_tensor, calib_tensor[:1])
        uv = xyz_tensor[:, :2, :]
        
        # 🔹 Sample colors from the image
        color = index(image_tensor[:1], uv).detach().cpu().numpy()[0].T
        color = color * 0.5 + 0.5  # Normalize to [0, 1]

        if 'calib_world' in data:
            calib_world = data['calib_world'].numpy()[0]
            verts = np.matmul(np.concatenate([verts, np.ones_like(verts[:, :1])], 1), inv(calib_world).T)[:, :3]

        # 🔹 Save mesh with colors
        save_obj_mesh_with_color(save_path, verts, faces, color)
    except Exception as e:
        print(" Mesh color generation error:", e)

def get_plane_from_landmarks(p1, p2):
    center = (p1 + p2) / 2
    normal = np.cross(p2 - p1, [0, 1, 0])
    return center, normal

def slice_mesh(mesh, center, normal):
    section = mesh.section(plane_origin=center, plane_normal=normal)
    if section is None:
        return None
    slice_2D, _ = section.to_planar()
    return slice_2D

def compute_girth(slice_2D):
    return slice_2D.length if slice_2D else None

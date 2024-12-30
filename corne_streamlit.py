import os
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array
import streamlit as st
from PIL import Image
import cv2
import plotly.graph_objects as go
from tensorflow.keras.backend import clear_session

clear_session()  # Clear any leftover session before loading the model

# Step 1: Save your trained model
MODEL_PATH = r"C:\Users\Umar Attique\Downloads\corn_disease.h5"

try:
    model = load_model(MODEL_PATH,compile=False)
    print("Model loaded successfully!")
except Exception as e:
    print(f"Error loading model: {e}") 

# Class names (update according to your dataset)
classes = ['Blight', 'Common_Rust', 'Gray_leaf_spot', 'Healthy']

# Streamlit App Title and Layout
st.set_page_config(page_title="Corn Disease Classification", layout="centered")
st.title("🌽 Real-Time Corn Leaf Disease Classification")

# Initialize session state for input method and webcam
if "input_method" not in st.session_state:
    st.session_state.input_method = "Upload an Image"
if "webcam_active" not in st.session_state:
    st.session_state.webcam_active = False
if "video_capture" not in st.session_state:
    st.session_state.video_capture = None
if "last_prediction" not in st.session_state:
    st.session_state.last_prediction = None
if "last_probabilities" not in st.session_state:
    st.session_state.last_probabilities = None

# Sidebar to switch between input methods
with st.sidebar:
    selected_method = st.radio(
        "Choose an Input Method", 
        ("Upload an Image", "Use Webcam"), 
        index=0 if st.session_state.input_method == "Upload an Image" else 1,
        key="sidebar_radio"
    )
    if st.session_state.input_method != selected_method:
        st.session_state.input_method = selected_method

# Reset webcam when switching to "Upload Image"
if st.session_state.input_method == "Upload an Image":
    if st.session_state.webcam_active:
        st.session_state.webcam_active = False
        if st.session_state.video_capture:
            st.session_state.video_capture.release()
        st.session_state.video_capture = None

# Preprocess function
def preprocess_image(image, target_size):
    if image.mode != 'RGB':
        image = image.convert('RGB')
    image = image.resize(target_size)
    image_array = img_to_array(image)
    image_array = np.expand_dims(image_array, axis=0)
    image_array /= 255.0  # Normalize
    return image_array

# Webcam prediction function
def webcam_prediction():
    st.warning("Ensure your webcam is enabled.")
    if not st.session_state.webcam_active:
        st.error("Webcam is not active. Please activate it first.")
        return
    
    cap = st.session_state.video_capture

    if not cap.isOpened():
        st.error("Failed to access webcam.")
        return

    stframe = st.empty()

    while st.session_state.webcam_active:
        ret, frame = cap.read()
        if not ret:
            st.error("Failed to read frame from webcam.")
            break

        # Image preprocessing and prediction
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        largest_contour = None
        max_area = 0

        for contour in contours:
            if cv2.contourArea(contour) > 500:  # Ignore small contours
                area = cv2.contourArea(contour)
                if area > max_area:
                    largest_contour = contour
                    max_area = area

        if largest_contour is not None:
            (x, y, w, h) = cv2.boundingRect(largest_contour)
            scale_height = int(h * 0.2)
            scale_y = y + h // 2 - scale_height // 2
            cv2.rectangle(frame, (x, scale_y), (x + w, scale_y + scale_height), (0, 255, 0), 2)

            scale_region = frame[scale_y:scale_y + scale_height, x:x + w]
            leaf_image_pil = Image.fromarray(cv2.cvtColor(scale_region, cv2.COLOR_BGR2RGB))
            processed_image = preprocess_image(leaf_image_pil, (224, 224))

            try:
                predictions = model.predict(processed_image)[0]
            except Exception as e:
                st.error(f"Prediction error: {e}")
                continue  # Skip this frame if prediction fails

            predicted_class = classes[np.argmax(predictions)]
            predicted_prob = predictions[np.argmax(predictions)] * 100

            # Store the last prediction and probabilities for pie chart
            st.session_state.last_prediction = predicted_class
            st.session_state.last_probabilities = predictions * 100

            cv2.putText(frame, f"{predicted_class}: {predicted_prob:.2f}%", 
                        (x, scale_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        stframe.image(frame_rgb, channels="RGB", caption="Webcam Feed with Scale", use_column_width=True)
        

    cap.release()
    cv2.destroyAllWindows()
    stframe.empty()


# Main Input Method Handling
if st.session_state.input_method == "Upload an Image":
    st.subheader("Upload an Image")
    uploaded_file = st.file_uploader("Choose an image file", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Image", use_column_width=True)

        if st.button("Predict Uploaded Image"):
            processed_image = preprocess_image(image, (224, 224))
            try:
                predictions = model.predict(processed_image)[0]
            except Exception as e:
                st.error(f"Prediction error: {e}")
            else:
                predicted_class = classes[np.argmax(predictions)]
                predicted_prob = predictions[np.argmax(predictions)] * 100

                st.success(f"Predicted Class: {predicted_class}")
                st.info(f"Confidence: {predicted_prob:.2f}%")

                fig = go.Figure(data=[go.Pie(labels=classes, values=predictions, hole=0.4)])
                fig.update_layout(title="Class Probabilities")
                st.plotly_chart(fig)

    else:
        st.info("Please upload an image to get started.")

elif st.session_state.input_method == "Use Webcam":
    st.subheader("Webcam Input")
    if st.button("Activate Webcam") and not st.session_state.webcam_active:
        st.session_state.video_capture = cv2.VideoCapture(0)
        st.session_state.webcam_active = True

    webcam_prediction()


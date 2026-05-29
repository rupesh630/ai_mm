import cv2
import mediapipe as mp
import zmq
import json
import time

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

def detect_gesture(hand_landmarks):
    """
    Very basic gesture detection using landmark coordinates.
    0: Wrist, 4: Thumb Tip, 8: Index Tip, 12: Middle Tip, 16: Ring Tip, 20: Pinky Tip
    """
    # Get y coordinates of tips and the joints right below them
    tips = [8, 12, 16, 20]
    pip_joints = [6, 10, 14, 18]
    
    fingers_open = 0
    for tip, pip in zip(tips, pip_joints):
        # In image coordinates, y=0 is top. If tip y < pip y, finger is extended.
        if hand_landmarks.landmark[tip].y < hand_landmarks.landmark[pip].y:
            fingers_open += 1
            
    # Thumb logic is a bit different based on x and y, but we'll simplify
    # Just counting the 4 fingers for now
    if fingers_open == 0:
        return "Fist"
    elif fingers_open == 4:
        return "Open Hand"
    elif fingers_open == 1 and hand_landmarks.landmark[8].y < hand_landmarks.landmark[6].y:
        return "Index Pointing"
    
    return "Unknown"

def run_agent():
    context = zmq.Context()
    socket = context.socket(zmq.PUSH)
    socket.connect("tcp://localhost:5556")
    
    cap = cv2.VideoCapture(0)
    print("Gesture Agent started. Press 'q' to quit.")
    
    last_gesture = None
    last_gesture_time = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        # Flip the frame horizontally for a selfie-view display
        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        results = hands.process(rgb_frame)
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                gesture = detect_gesture(hand_landmarks)
                
                # Debounce logic: only send if it's a new gesture or it's been a while
                current_time = time.time()
                if gesture != "Unknown" and (gesture != last_gesture or (current_time - last_gesture_time) > 2.0):
                    print(f"Detected Gesture: {gesture}")
                    message = {"type": "gesture", "value": gesture}
                    socket.send_string(json.dumps(message))
                    last_gesture = gesture
                    last_gesture_time = current_time
                    
                # Put text on image
                cv2.putText(frame, f"Gesture: {gesture}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        cv2.imshow('Gesture Agent', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_agent()

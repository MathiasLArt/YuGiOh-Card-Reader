import cv2


class Webcam:
    def __init__(self, camera_index=0):
        self.cap = cv2.VideoCapture(camera_index)

        if not self.cap.isOpened():
            print(f"Error: Could not open camera with index {camera_index}.")
            exit()

    def __del__(self):
        self.cap.release()

    def get_frame(self):
        ret, frame = self.cap.read()

        if not ret:
            print("Error: Could not read frame.")
            return None

        return frame

    def show_webcam(self):
        while True:
            frame = self.get_frame()

            if frame is None:
                break

            cv2.imshow("Webcam Feed", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        cv2.destroyAllWindows()

    def release(self):
        cv2.destroyAllWindows()

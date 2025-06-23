#========================PySpin=============================
import os
import pyspin as PySpin
import matplotlib.pyplot as plt
import sys
import keyboard
import time
import serial
#========================Model============================
from PIL import Image
import torchvision.transforms as transforms
import torch
import torch.nn.functional as F
import torch.nn as nn
#=========================OpenCV=============================
import numpy as np
import cv2 as cv

#Arduino setting
ser = serial.Serial('COM6', 9600)
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


os.chdir(os.path.dirname(os.path.abspath(__file__)))
current_cwd = os.getcwd()
print(f"Present working directory: {current_cwd}")

#Create Directory which Detected image will be saved as you want
save_dir='Detected_images'

#Setting device
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using {device} device")
global continue_recording
continue_recording = True

#ROI parameters setting for fixed location of the camera 
start_x=162
start_y=290
test_width=700

#dataset transformer
transform_test = transforms.Compose([
    transforms.Resize((256, 256)),
    transforms.ToTensor()
])

text=0

class ConvAutoencoder(nn.Module):
    def __init__(self):
        super(ConvAutoencoder, self).__init__()
        self.encoder = nn.Sequential(
            nn.Conv2d(3, 64, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            nn.Conv2d(64, 128, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            nn.Conv2d(128, 256, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2, 2)
        )
        self.decoder = nn.Sequential(
            nn.Conv2d(256, 256, 3, padding=1),
            nn.ReLU(),
            nn.Upsample(scale_factor=2),
            nn.Conv2d(256, 128, 3, padding=1),
            nn.ReLU(),
            nn.Upsample(scale_factor=2),
            nn.Conv2d(128, 64, 3, padding=1),
            nn.ReLU(),
            nn.Upsample(scale_factor=2),
            nn.Conv2d(64, 3, 3, padding=1),
            nn.Sigmoid()
        )

    def forward(self, x):
        x = self.encoder(x)
        x = self.decoder(x)
        return x


#Function for judging whether a nut is defected
def predict_anomaly(model, image_tensor, threshold):
    model.eval()
    with torch.no_grad():
        output = model(image_tensor)
        mse = F.mse_loss(output, image_tensor, reduction='none')
        mse = mse.mean(dim=[1, 2, 3]) 
        pred='a0'

        #Anomaly
        if mse>threshold:
            pred='a1'

        print(f"Reconstruction Error: {mse.item():.6f}")
        print("Prediction:", "🤬 Anomaly" if pred == 'a1' else "😁 Normal")
        
        return pred
    


#Safe shutdown mechanism to terminate the camera capture loop.
def handle_close(evt):
    global continue_recording
    continue_recording = False

#Acquiring and displaying image
def acquire_and_display_images(cam, nodemap, nodemap_tldevice):
    global continue_recording

    result=True
    sNodemap = cam.GetTLStreamNodeMap()

    # Change bufferhandling mode to NewestOnly
    node_bufferhandling_mode = PySpin.CEnumerationPtr(sNodemap.GetNode('StreamBufferHandlingMode'))
    if not PySpin.IsReadable(node_bufferhandling_mode) or not PySpin.IsWritable(node_bufferhandling_mode):
        print('Unable to set stream buffer handling mode.. Aborting...')
        return False

    # Retrieve entry node from enumeration node
    node_newestonly = node_bufferhandling_mode.GetEntryByName('NewestOnly')
    if not PySpin.IsReadable(node_newestonly):
        print('Unable to set stream buffer handling mode.. Aborting...')
        return False

    # Retrieve integer value from entry node
    node_newestonly_mode = node_newestonly.GetValue()

    # Set integer value from entry node as new value of enumeration node
    node_bufferhandling_mode.SetIntValue(node_newestonly_mode)

    print('*** IMAGE ACQUISITION ***\n')
    try:
        node_acquisition_mode = PySpin.CEnumerationPtr(nodemap.GetNode('AcquisitionMode'))
        if not PySpin.IsReadable(node_acquisition_mode) or not PySpin.IsWritable(node_acquisition_mode):
            #print('Unable to set acquisition mode to continuous (enum retrieval). Aborting...')
            return False

        # Retrieve entry node from enumeration node
        node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName('Continuous')
        if not PySpin.IsReadable(node_acquisition_mode_continuous):
            #print('Unable to set acquisition mode to continuous (entry retrieval). Aborting...')
            return False

        # Retrieve integer value from entry node
        acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()

        # Set integer value from entry node as new value of enumeration node
        node_acquisition_mode.SetIntValue(acquisition_mode_continuous)
        print('Acquisition mode set to continuous...')

        #Aquiring image
        cam.BeginAcquisition()
        print('Acquiring images...')


        device_serial_number = ''
        node_device_serial_number = PySpin.CStringPtr(nodemap_tldevice.GetNode('DeviceSerialNumber'))
        if PySpin.IsReadable(node_device_serial_number):
            device_serial_number = node_device_serial_number.GetValue()
            print('Device serial number retrieved as %s...' % device_serial_number)

        # Close program
        print('Press enter to close the program..')

        # Figure(1) is default so you can omit this line. Figure(0) will create a new window every time program hits this line
        fig = plt.figure(1)

        # Close the GUI when close event happens
        fig.canvas.mpl_connect('close_event', handle_close)

        # Setting GPU
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Model instantiation and loading pre-trained weights
        model = ConvAutoencoder().to(device)
        model.load_state_dict(torch.load("FINAL_MODEL.pth", map_location=device))
        model.eval()  


        #create background image
        if cam.IsStreaming():
            backgournd_result = cam.GetNextImage(1000)

        else:
            print("Camera is not streaming.")
            return False
        
        
        #Save initial background 
        raw_background=backgournd_result
        processor = PySpin.ImageProcessor()
        processor.SetColorProcessing(PySpin.SPINNAKER_COLOR_PROCESSING_ALGORITHM_HQ_LINEAR)
        background_rgb=processor.Convert(raw_background, PySpin.PixelFormat_RGB8)
        background=background_rgb.GetNDArray()
        background=background[start_y:start_y+test_width,start_x:start_x+test_width]
        
        
        #Initialize time of precious frame
        last_saved_time=0
        
        #Initialize the flag for judging whether the nut is anomaly 
        flag = 'a0'
        ser.write(str(flag).encode()) 
       
        #Initialize previous frame
        before=np.zeros_like(background)
        
        # Retrieve and display images
        while(continue_recording):
            
            try:
                
                #Acquire the image from the camera.
                if cam.IsStreaming():
                    image_result = cam.GetNextImage(1000)

                else:
                    print("Camera is not streaming.")
                    return False
                

                #  Ensure image completion
                if image_result.IsIncomplete():
                    print('Image incomplete with image status %d ...' % image_result.GetImageStatus())

                else:                    
                    
                    # Getting the image data as a numpy array
                    flag = 'a0'
                    ser.write(str(flag).encode()) 
                    
                    #current: 700x700 raw image
                    raw_image=image_result
                    processor.SetColorProcessing(PySpin.SPINNAKER_COLOR_PROCESSING_ALGORITHM_HQ_LINEAR)
                    image_rgb = processor.Convert(raw_image, PySpin.PixelFormat_RGB8)
                    current = image_rgb.GetNDArray().copy()
                    current=current[start_y:start_y+test_width,start_x:start_x+test_width]
                    
                    #Gray images for calculating difference between previous and current frame
                    gray_current=cv.cvtColor(current,cv.COLOR_RGB2GRAY)
                    gray_before=cv.cvtColor(before,cv.COLOR_RGB2GRAY)

                    #Calculate difference between previous and current frame
                    diff=cv.absdiff(gray_current,gray_before)
                    _,diff=cv.threshold(diff,100,255,cv.THRESH_BINARY)
                    
                    #Declare change ratio 
                    change_ratio = np.sum(diff > 0) / diff.size
                    

                    #Time of current frame
                    current_time=time.time()
                    
                    #Initialize variable for judge whether picture is taken
                    picture_is_taken=0
                    
                    
                    #If Change ratio is bigger than 4.95% and more than two seconds have passed since the last photo was taken, save the frame
                    if (change_ratio > 0.0495) and ((current_time-last_saved_time)>2) :  
                        
                        last_saved_time = current_time
                        
                        
                        timestamp = time.strftime("%Y%m%d_%H%M%S")  
                        
                        
                        os.makedirs(save_dir,exist_ok=True)
                        current_bgr=cv.cvtColor(current, cv.COLOR_RGB2BGR)
                        #cropped_before_bgr=cv.cvtColor(cropped_before, cv.COLOR_RGB2BGR)

                        filename = os.path.join(save_dir, f"detected_{timestamp}.jpg")
                        cv.imwrite(filename, current_bgr)
                        #print(f" Object detected! Image saved as {filename}")
                        
                        #Notification: Photo has been taken
                        picture_is_taken=1
                        
                       
                    #To detect other objects as well, save current frame as previous frame
                    before=current

                    #Image prepocessing for taken image
                    if picture_is_taken:
                        
                        #source Image
                        source=cv.imread(filename)
                        source_gray=cv.cvtColor(source,cv.COLOR_RGB2GRAY)

                        #Find threshold of the image
                        _, thresh = cv.threshold(source_gray, 127, 255, cv.THRESH_BINARY)

                        #Find the largest contour of the image
                        contours, _ = cv.findContours(thresh, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)                       
                        
                        #Continue the process only when the objet contour is captured
                        if contours: 
                            largest_contour = max(contours, key=cv.contourArea)
                        else:
                            continue
                        
                        #Copy the source image and draw the largest contour on it
                        contour_image=source.copy()
                        cv.drawContours(contour_image,[largest_contour],-1,(255,0,0),3)
                        
                        #Find circumscribed circle and center point of the largest contour 
                        (x, y), radius = cv.minEnclosingCircle(largest_contour)
                        center_x, center_y = int(x), int(y)

                        #Calculate crop area
                        crop_size = 400
                        half_crop = crop_size // 2
                        h, w = source.shape[:2]

                        #Exception handling to prevent exceeding image boundaries
                        x1 = max(center_x - half_crop, 0)
                        y1 = max(center_y - half_crop, 0)
                        x2 = min(center_x + half_crop, w)
                        y2 = min(center_y + half_crop, h)

                        #Crop a 400×400 pixel region centered on the previously obtained contour’s center
                        cropped_source=source[y1:y2, x1:x2]

                        #Treat the cropped image as the image to send to the model.
                        image_to_model=cv.cvtColor(cropped_source,cv.COLOR_RGB2GRAY)
                        
                        #Save the cropped image in your directory
                        cropped_filename = os.path.join(save_dir, f"cropped_detected_{timestamp}.jpg")
                        cv.imwrite(cropped_filename, image_to_model)

                        #Convert the preprocessed image into a tensor format suitable for input to the model.
                        taken_nut = Image.open(cropped_filename).convert("RGB")
                        input_tensor = transform_test(taken_nut)
                        input_tensor = input_tensor.unsqueeze(0)
                        input_tensor = input_tensor.to(device)
                        
                        #Put the tensor in the Autoencoder model and set the suitable threshold as we got from model training process 
                        flag = predict_anomaly(model, input_tensor, threshold=0.0011)
                        
                        #Send the flag to the arduino. When an anomalous nut is detected, the Arduino turns on the LED and stops the conveyor belt.
                        ser.write(str(flag).encode()) 
                        
                        #When an anomalous nut is detected, wait until the Arduino has completed the commands to stop the conveyor belt and turn on the LED, and sends back ‘ready’.
                        if flag == 'a1':

                            while True:
                                if ser.in_waiting > 0:  
                                    line = ser.readline().decode().strip()
                                    
                                    if line == 'ready':
                                        break
                    
                    #Display the current image
                    plt.imshow(current)
                    plt.pause(0.001)
                    plt.clf()
                    
                    # If user presses enter, close the program
                    if keyboard.is_pressed('ENTER'):
                        print('Program is closing...')
                        
                        # Close figure
                        plt.close('all')             
                        input('Done! Press Enter to exit...')
                        continue_recording=False                        

                image_result.Release()

            except PySpin.SpinnakerException as ex:
                # Catch any Spinnaker-specific exceptions during image acquisition/processing
                print('Error: %s' % ex)
                # Return False to indicate that the acquisition loop failed
                return False

        cam.EndAcquisition()

    except PySpin.SpinnakerException as ex:
        # Catch any Spinnaker-specific exceptions around the overall acquisition setup/teardown
        print('Error: %s' % ex)

        # Return False to signal that the main function encountered an error
        return False

    return True


def run_single_camera(cam):

    try:
        result = True

        nodemap_tldevice = cam.GetTLDeviceNodeMap()

        # Initialize camera
        cam.Init()

        # Retrieve GenICam nodemap
        nodemap = cam.GetNodeMap()
        node_pixel_format = PySpin.CEnumerationPtr(nodemap.GetNode('PixelFormat'))
        node_pixel_format_rgb = node_pixel_format.GetEntryByName('RGB8')

        # Check if the RGB8 pixel format entry is available and readable
        if PySpin.IsAvailable(node_pixel_format_rgb) and PySpin.IsReadable(node_pixel_format_rgb):
            
            # Get the integer value corresponding to the RGB8 format
            pixel_format_rgb_value = node_pixel_format_rgb.GetValue()
            
            # Set the camera's pixel format to RGB8 using the retrieved value
            node_pixel_format.SetIntValue(pixel_format_rgb_value)
            print("PixelFormat set to RGB8.")
        else:
            # If RGB8 is not supported or not accessible, notify the user
            print("Unable to set PixelFormat to RGB8.")

        # Acquire images
        result &= acquire_and_display_images(cam, nodemap, nodemap_tldevice)

        # Deinitialize camera
        cam.DeInit()

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        result = False

    return result


def main():

    try:
        # Attempt to create and open a temporary test file to verify write permissions
        test_file = open('test.txt', 'w+')
    except IOError:
        # If file creation fails, inform the user and exit the program gracefully
        print('Unable to write to current directory. Please check permissions.')
        input('Press Enter to exit...')
        return False

    # Close the test file now that write permissions are confirmed
    test_file.close()

    # Remove the temporary test file to clean up
    os.remove(test_file.name)


    # Initialize the overall result flag as True (will be updated based on camera operations)
    result = True

    # Retrieve singleton reference to system object
    system = PySpin.System.GetInstance()

    # Get current library version
    version = system.GetLibraryVersion()
    print('Library version: %d.%d.%d.%d' % (version.major, version.minor, version.type, version.build))

    # Retrieve list of cameras from the system
    cam_list = system.GetCameras()
    
    # Retrieve the number of cameras currently connected to the system
    num_cameras = cam_list.GetSize()

    print('Number of cameras detected: %d' % num_cameras)
    # Finish if there are no cameras
    if num_cameras == 0:

        # Clear camera list before releasing system
        cam_list.Clear()

        # Release system instance
        system.ReleaseInstance()

        print('Not enough cameras!')
        input('Done! Press Enter to exit...')
        return False

    # Run example on each camera
    for i, cam in enumerate(cam_list):
        result &= run_single_camera(cam)

    # Release reference to camera
    del cam

    # Clear camera list before releasing system
    cam_list.Clear()

    # Release system instance
    system.ReleaseInstance()

    input('Done! Press Enter to exit...')
    return result


if __name__ == '__main__':
    if main():
        sys.exit(0)
    else:
        sys.exit(1)

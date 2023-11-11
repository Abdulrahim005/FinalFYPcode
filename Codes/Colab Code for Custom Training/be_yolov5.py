# -*- coding: utf-8 -*-
"""BE-Yolov5

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1--gLxfHKBuIdc5A9QItsn_tFtoIk5y5R

# Custom Training with YOLOv5 - SLUG ROBOT COLLECTOR 🤖

In this tutorial, we assemble a dataset and train a custom YOLOv5 model to recognize the objects in our dataset. To do so we will take the following steps:

* Gather a dataset of images and label our dataset
* Export our dataset to YOLOv5
* Train YOLOv5 to recognize the objects in our dataset
* Evaluate our YOLOv5 model's performance
* Run test inference to view our model at work



![](https://uploads-ssl.webflow.com/5f6bc60e665f54545a1e52a5/615627e5824c9c6195abfda9_computer-vision-cycle.png)

# Step 1: Install Requirements
"""

# Commented out IPython magic to ensure Python compatibility.
#clone YOLOv5 to our directory
!git clone https://github.com/ultralytics/yolov5  # clone repo
# %cd yolov5
# %pip install -qr requirements.txt # install dependencies

import torch
import os
from IPython.display import Image, clear_output  # to display images

print(f"Setup complete. Using torch {torch.__version__} ({torch.cuda.get_device_properties(0).name if torch.cuda.is_available() else 'CPU'})")

"""#Step 2: To get the labelled photos with their labels files, we need to get them from our google drive and uncompress them. """

# Mount Our Drive
from google.colab import drive
drive.mount('/content/gdrive') # if getting an error type drive instead of gdrive

# Unzip the compressed photos file to /content
!unzip "/content/gdrive/MyDrive/NewSlugTraining/trainData.zip" -d "/content"

# Copy the yaml file inside the data folder in the yolov5 repo
!cp '/content/trainData/custom_dataset.yaml' '/content/yolov5/data'

# To set up environment
os.environ["DATASET_DIRECTORY"] = "/content/datasets"

"""# Step 3: Train Our Custom YOLOv5 model

Here, we are able to pass a number of arguments:
- **img:** define input image size
- **batch:** determine batch size
- **epochs:** define the number of training epochs. (Note: often, 3000+ are common here!)
- **data:** Our dataset locaiton is saved in the `dataset.location`
- **weights:** specify a path to weights to start transfer learning from. Here we choose the generic COCO pretrained checkpoint.
- **cache:** cache images for faster training
"""

# Make sure that the path of these files are "custom_dataset.yaml and yolov5.pt" are correct.
# To find the full path: right click the file and copy path
!python py --img 416 --batch 32 --epochs 130 --data custom_dataset.yaml --weights yolov5s.pt --cache

"""# Evaluate Custom YOLOv5 Detector Performance
Training losses and performance metrics are saved to Tensorboard and also to a logfile.

If you are new to these metrics, the one you want to focus on is `mAP_0.5` - learn more about mean average precision [here](https://blog.roboflow.com/mean-average-precision/).
"""

# Commented out IPython magic to ensure Python compatibility.
# Start tensorboard
# Launch after you have started training
# logs save in the folder "runs"
# %load_ext tensorboard
# %tensorboard --logdir runs

"""#Run Inference  With Trained Weights
Run inference with a pretrained checkpoint on contents of `test/images` folder downloaded from drive

"""

!python detect.py --weights best.pt --img 416 --conf 0.5 --source '/content/videos/videos' --include onnx

"""# Conclusion:

Now you've trained a custom YOLOv5 model to recognize your custom objects. We can download the model with the new weigths using the below command
"""

from google.colab import files
files.download('./runs/train/exp/weights/best.pt')
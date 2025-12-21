import os
from util_func import masterfile_creation, mastergeometry_creation
from warnings import filterwarnings

filterwarnings('ignore')

# Masterfile creation
masterfile_creation(['B25057', 'B25058', 'B25059'], API_key = os.environ['SECRET_KEY'])

# Mastergeometry creation
mastergeometry_creation()
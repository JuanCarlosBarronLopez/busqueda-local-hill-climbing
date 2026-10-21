"""Permite que ``pytest`` importe el paquete ``hillclimb`` desde la raíz."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

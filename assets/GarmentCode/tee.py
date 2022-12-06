from pathlib import Path
from datetime import datetime
from copy import deepcopy
from scipy.spatial.transform import Rotation as R

# Custom
import pypattern as pyp
from customconfig import Properties


class SleevePanel(pyp.Panel):
    """Simple panel for a sleeve"""

    def __init__(self, name, length=35, arm_width=30, ease=3) -> None:
        super().__init__(name)

        width = (arm_width + ease) / 2 
        self.edges = pyp.ops.simple_loop([0, width], [length, width], [length - 7, 0])

        # default placement
        self.translate_by([-length - 20, 15, 0])

        self.interfaces = [
            pyp.InterfaceInstance(self, self.edges[1]),
            pyp.InterfaceInstance(self, self.edges[2]),
            pyp.InterfaceInstance(self, self.edges[3]),
        ]

class TorsoPanel(pyp.Panel):
    """Panel for the front of upper garments"""

    def __init__(self, name, length=50, neck_w=15, sholder_w=40, c_depth=15, ease=3) -> None:
        super().__init__(name)

        width = sholder_w + ease
        sholder_top_l = (width - neck_w) / 2 
        self.edges = pyp.ops.simple_loop(
            [0, length], 
            [sholder_top_l, length], 
            [width / 2, length - c_depth], 
            [sholder_top_l + neck_w, length], 
            [width, length], 
            [width, 0], 
            )

        # default placement
        self.translate_by([-width / 2, 30 - length, 0])

        self.interfaces = [
            pyp.InterfaceInstance(self, self.edges[0]),
            pyp.InterfaceInstance(self, self.edges[1]),
            pyp.InterfaceInstance(self, self.edges[4]),
            pyp.InterfaceInstance(self, self.edges[5]),
        ]

class TShirt(pyp.Component):
    """Definition of a simple T-Shirt"""

    def __init__(self) -> None:
        super().__init__(self.__class__.__name__)

        # sleeves
        self.rf_sleeve = SleevePanel('rf_sleeve').translate_by([0, 0, 15])
        self.lf_sleeve = SleevePanel('lf_sleeve').translate_by([0, 0, 15]).mirror()
        self.rb_sleeve = SleevePanel('rb_sleeve').translate_by([0, 0, -15])
        self.lb_sleeve = SleevePanel('lb_sleeve').mirror().translate_by([0, 0, -15])

        # Torso
        self.ftorso = TorsoPanel('front').translate_by([0, 0, 20])
        self.btorso = TorsoPanel('back').translate_by([0, 0, -20])

        # DEBUG
        for e in self.rf_sleeve.edges:
            print(e.start, e.end)

        # Order of edges updated after (autonorm)..
        # TODO Simplify the choice of the edges to project from/to (regardless of autonorm)
        pyp.ops.cut_corner([self.rf_sleeve.edges[1]], self.ftorso, 5, 6)
        pyp.ops.cut_corner([self.lf_sleeve.edges[2]], self.ftorso, 1, 2)
        pyp.ops.cut_corner([self.rb_sleeve.edges[2]], self.btorso, 0, 1)
        pyp.ops.cut_corner([self.lb_sleeve.edges[1]], self.btorso, 5, 6)
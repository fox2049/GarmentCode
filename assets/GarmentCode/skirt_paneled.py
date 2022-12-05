import json
from pathlib import Path
from datetime import datetime
from copy import deepcopy
from scipy.spatial.transform import Rotation as R

# Custom
import pypattern as pyp
from customconfig import Properties

class RuffleSkirtPanel(pyp.Panel):
    """One panel of a panel skirt with ruffles on the waist"""

    def __init__(self, name, ruffles=1.5, waist_length=70, length=70, bottom_cut=10) -> None:
        super().__init__(name)

        base_width = waist_length / 2
        panel_low_width = base_width + 40
        x_shift_top = (panel_low_width - base_width) / 2

        # define edge loop
        # TODO SequentialObject?
        self.edges = pyp.ops.side_with_cut([0,0], [x_shift_top, length], start_cut=bottom_cut / length)
        self.edges.append(pyp.LogicalEdge(self.edges[-1].end, [x_shift_top + base_width, length], ruffle_rate=ruffles))  # on the waist
        self.edges += pyp.ops.side_with_cut(self.edges[-1].end, [panel_low_width, 0], end_cut=bottom_cut / length)
        self.edges.append(pyp.LogicalEdge(self.edges[-1].end, self.edges[0].start))

        # define interface
        # TODO references with vs without cuts? What is the cut parameter is zero?
        # TODO More semantic references?
        self.interfaces.append(pyp.InterfaceInstance(self, self.edges[1]))
        # Create ruffles by the differences in edge length
        # NOTE ruffles are only created when connecting with something
        self.interfaces.append(pyp.InterfaceInstance(self, self.edges[2]))
        self.interfaces.append(pyp.InterfaceInstance(self, self.edges[3]))

class ThinSkirtPanel(pyp.Panel):
    """One panel of a panel skirt"""

    def __init__(self, name, top_width=10) -> None:
        super().__init__(name)

        # define edge loop
        self.edges = [pyp.LogicalEdge([0,0], [10, 70])]   # TODO SequentialObject?
        self.edges.append(pyp.LogicalEdge(self.edges[-1].end, [10 + top_width, 70]))
        self.edges.append(pyp.LogicalEdge(self.edges[-1].end, [20 + top_width, 0]))
        self.edges.append(pyp.LogicalEdge(self.edges[-1].end, self.edges[0].start))

        self.interfaces.append(pyp.InterfaceInstance(self, self.edges[0]))
        self.interfaces.append(pyp.InterfaceInstance(self, self.edges[1]))
        self.interfaces.append(pyp.InterfaceInstance(self, self.edges[2]))


class WBPanel(pyp.Panel):
    """One panel for a panel skirt"""

    def __init__(self, name) -> None:
        super().__init__(name)

        # define edge loop
        self.edges = [pyp.LogicalEdge([0,0], [0, 10])]   # TODO SequentialObject?
        self.edges.append(pyp.LogicalEdge(self.edges[-1].end, [35, 10]))
        self.edges.append(pyp.LogicalEdge(self.edges[-1].end, [35, 0]))
        self.edges.append(pyp.LogicalEdge(self.edges[-1].end, self.edges[0].start))

        # define interface
        self.interfaces.append(pyp.InterfaceInstance(self, self.edges[0]))
        self.interfaces.append(pyp.InterfaceInstance(self, self.edges[1]))
        self.interfaces.append(pyp.InterfaceInstance(self, self.edges[2]))
        self.interfaces.append(pyp.InterfaceInstance(self, self.edges[3]))


class Skirt2(pyp.Component):
    """Simple 2 panel skirt"""
    def __init__(self, ruffle_rate=1) -> None:
        super().__init__(self.__class__.__name__)

        self.front = RuffleSkirtPanel('front', ruffle_rate)
        self.front.translate_by([-40, -75, 20])

        self.back = RuffleSkirtPanel('back', ruffle_rate)
        self.back.translate_by([-40, -75, -15])

        self.stitching_rules = [
            (self.front.interfaces[0], self.back.interfaces[0]),
            (self.front.interfaces[2], self.back.interfaces[2])
        ]

        # TODO use dict for interface references?
        # Reusing interfaces of sub-panels as interfaces of this component
        self.interfaces = [
            self.front.interfaces[1],
            self.back.interfaces[1]
        ]  


# With waistband
class WB(pyp.Component):
    """Simple 2 panel waistband"""
    def __init__(self) -> None:
        super().__init__(self.__class__.__name__)

        self.front = WBPanel('wb_front')
        self.front.translate_by([-20, -2, 20])
        self.back = WBPanel('wb_back')
        self.back.translate_by([-20, -2, -15])

        self.stitching_rules = [
            (self.front.interfaces[0], self.back.interfaces[0]),
            (self.front.interfaces[2], self.back.interfaces[2])
        ]

        self.interfaces = [
            self.front.interfaces[3],
            self.back.interfaces[3]
        ]


class SkirtWB(pyp.Component):
    def __init__(self, ruffle_rate=1.5) -> None:
        super().__init__(f'{self.__class__.__name__}_{ruffle_rate:.1f}')

        self.wb = WB()
        self.skirt = Skirt2(ruffle_rate=ruffle_rate)

        self.stitching_rules = [
            (self.wb.interfaces[0], self.skirt.interfaces[0]),
            (self.wb.interfaces[1], self.skirt.interfaces[1])
        ]


class SkirtManyPanels(pyp.Component):
    """Round Skirt with many panels"""

    def __init__(self, n_panels = 4) -> None:
        super().__init__(f'{self.__class__.__name__}_{n_panels}')

        self.n_panels = n_panels

        self.front = ThinSkirtPanel('front', 72 / n_panels)
        self.front.translate_by([-72 / n_panels, -75, 20])

        self.subs = pyp.ops.distribute_Y(self.front, n_panels)

        # Stitch new components
        for i in range(1, n_panels):
            self.stitching_rules.append((self.subs[i - 1].interfaces[2], self.subs[i].interfaces[0]))
        self.stitching_rules.append((self.subs[-1].interfaces[2], self.subs[0].interfaces[0]))

        # No interfaces
import numpy as np
# Custom
from pattern.core import BasicPattern
from pattern.wrappers import VisPattern
from .base import BaseComponent

class Component(BaseComponent):
    """Garment element (or whole piece) composed of simpler connected garment elements"""

    # TODO Overload copy -- respecting edge sequences

    def __init__(self, name) -> None:
        super().__init__(name)

        self.subs = []  # list of generative sub-components

    # Operations -- update object in-place
    # All return self object to allow chained operations
    def translate_by(self, delta_vector):
        """Translate component by a vector"""
        for subs in self._get_subcomponents():
            subs.translate_by(delta_vector)
        return self
    
    def translate_to(self, new_translation):
        """Set panel translation to be exactly that vector"""
        # FIXME does not preserve relative placement of subcomponents
        for subs in self._get_subcomponents():
            subs.translate_to(new_translation)
        return self

    def place_below(self, comp: BaseComponent, gap=2):
        """Place below the provided component"""
        other_bbox = comp.bbox3D()
        curr_bbox = self.bbox3D()

        self.translate_by([0, other_bbox[0][1] - curr_bbox[1][1] - gap, 0])

        return self

    def rotate_by(self, delta_rotation):
        """Rotate component by a given rotation"""
        for subs in self._get_subcomponents():
            subs.rotate_by(delta_rotation)
        return self
    
    def rotate_to(self, new_rot):
        """Set panel rotation to be exactly given rotation"""
        for subs in self._get_subcomponents():
            subs.rotate_to(new_rot)
        return self

    def mirror(self, axis=[0, 1]):
        """Swap this component with it's mirror image by recursively mirroring sub-components
        
            Axis specifies 2D axis to swap around: Y axis by default
        """
        for subs in self._get_subcomponents():
            subs.mirror(axis)
        return self

    # Build the component -- get serializable representation
    def assembly(self):
        """Construction process of the garment component
        
        Returns: simulator friendly description of component sewing pattern
        """
        spattern = VisPattern(view_ids=True)
        spattern.name = self.name

        subs = self._get_subcomponents()
        if not subs:
            return spattern

        # Simple merge of sub-component representations
        for sub in subs:
            sub_raw = sub().pattern

            # simple merge of panels
            spattern.pattern['panels'] = {**spattern.pattern['panels'], **sub_raw['panels']}

            # of stitches
            spattern.pattern['stitches'] += sub_raw['stitches']

        spattern.pattern['stitches'] += self.stitching_rules.assembly()

        return spattern   

    # Utilities
    def bbox3D(self):
        """Evaluate 3D bounding box of the current component"""
        
        subs = self._get_subcomponents()
        bboxes = [s.bbox3D() for s in subs]

        mins = np.vstack([b[0] for b in bboxes])
        maxes = np.vstack([b[1] for b in bboxes])

        return mins.min(axis=0), maxes.max(axis=0)


    def _get_subcomponents(self):
        """Unique set of subcomponents defined in the self.subs list or as attributes of the object"""

        all_attrs = [getattr(self, name) for name in dir(self) if name[:2] != '__' and name[-2:] != '__']
        return list(set([att for att in all_attrs if isinstance(att, BaseComponent)] + self.subs))



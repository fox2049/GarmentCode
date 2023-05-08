import pypattern as pyp
from scipy.spatial.transform import Rotation as R
import numpy as np

# TODOLOW front more narrow then the back
# TODO Fix dependent (Godet) skirt
class FittedSkirtPanel(pyp.Panel):
    """Fitted panel for a pencil skirt
    """
    def __init__(
        self, name, waist, hips,   # TODO Half measurement instead of a quarter
        hips_depth, length, low_width, rise=1,
        dart_position=None,  dart_frac=0.5,
        cut=0,
        ruffle=False) -> None:
        # TODOLOW Only the parameters that differ between front/back panels?
        """
            Basic pant panel with option to be fitted (with darts) or ruffled at waist area.
            
            * rise -- the pant rize. 1 = waistline, 0 = crotch line (I'd not recommend to go all the way to zero 😅)
            * dart_position -- from the center of the body to the dart
            * ruffle -- use ruffles instead of fitting with darts. If ruffle = False, the dart_position needs to be specified
            * crotch_extention amount of exta fabric between legs
        """
        super().__init__(name)

        # adjust for a rise
        adj_crotch_depth = rise * hips_depth
        adj_waist = hips - rise * (hips - waist)
        dart_depth = hips_depth * dart_frac
        dart_depth = max(dart_depth - (hips_depth - adj_crotch_depth), 0)

        # eval shape
        # Check for ruffle
        if ruffle:
            ruffle_rate = hips / adj_waist
            adj_waist = hips 
        else:
            ruffle_rate = 1

        # amount of extra fabric
        w_diff = hips - adj_waist   # Assume its positive since waist is smaller then hips
        # We distribute w_diff among the side angle and a dart 
        hw_shift = w_diff / 6

        right = pyp.esf.curve_from_extreme(
            [hips - low_width, 0],    
            [hw_shift, length + adj_crotch_depth],
            target_extreme=[0, length]
        )
        top = pyp.Edge(right.end, [hips * 2 - hw_shift, length + adj_crotch_depth])
        left = pyp.esf.curve_from_extreme(
            top.end,
            [hips + low_width, 0],
            target_extreme=[hips * 2, length]
        )
        self.edges = pyp.EdgeSequence(right, top, left).close_loop()
        bottom = self.edges[-1]

        if cut:  # add a cut
            # Use long and thin disconnected dart for a cutout
            new_edges, _, int_edges = pyp.ops.cut_into_edge(
                pyp.esf.dart_shape(1, cut),    # 1 cm  # TODOLOW width could also be a parameter?
                bottom, 
                offset= bottom.length() / 2,
                right=True)

            self.edges.substitute(bottom, new_edges)
            bottom = int_edges

        # Default placement
        self.top_center_pivot()
        self.translation = [-hips / 2, 5, 0]

        # Out interfaces (easier to define before adding a dart)
        self.interfaces = {
            'bottom': pyp.Interface(self, bottom),
            'right': pyp.Interface(self, right), 
            'left': pyp.Interface(self, left),  
        }

        # Add top dart 
        if not ruffle and dart_depth: 
            # TODO: routine for multiple darts
            # FIXME front/back darts don't appear to be located at the same position
            dart_width = w_diff - hw_shift
            dart_shape = pyp.esf.dart_shape(dart_width, dart_depth)
            top_edge_len = top.length()
            top_edges, dart_edges, int_edges = pyp.ops.cut_into_edge(
                dart_shape, 
                top, 
                offset=(top_edge_len / 2 - dart_position),   # from the middle of the edge
                right=True)
            
            self.stitching_rules.append(
                (pyp.Interface(self, dart_edges[0]), pyp.Interface(self, dart_edges[1])))

            left_edge_len = top_edges[-1].length()
            top_edges_2, dart_edges, int_edges_2 = pyp.ops.cut_into_edge(
                dart_shape, 
                top_edges[-1], 
                offset=left_edge_len - top_edge_len / 2 + dart_position, # from the middle of the edge
                right=True)

            self.stitching_rules.append(
                (pyp.Interface(self, dart_edges[0]), pyp.Interface(self, dart_edges[1])))
            
            # Update panel
            top_edges.substitute(-1, top_edges_2)
            int_edges.substitute(-1, int_edges_2)

            self.interfaces['top'] = pyp.Interface(self, int_edges) 
            self.edges.substitute(top, top_edges)

            # Second dart

        else: 
            self.interfaces['top'] = pyp.Interface(self, self.edges[1], ruffle=ruffle_rate)   


class PencilSkirt(pyp.Component):
    def __init__(self, body, design) -> None:
        super().__init__(self.__class__.__name__)

        design = design['pencil-skirt']

        self.front = FittedSkirtPanel(
            f'skirt_f',   
            body['waist'] / 4, 
            body['hips'] / 4, 
            body['hips_line'],
            design['length']['v'],
            low_width=design['flare']['v'] * body['hips'] / 4,
            rise=design['rise']['v'],
            dart_position=body['bust_points'] / 2,
            dart_frac=1.7,  # Diff for front and back
            ruffle=design['ruffle']['v'][0], 
            cut=design['front_cut']['v']
        ).translate_to([0, body['waist_level'], 25])
        self.back = FittedSkirtPanel(
            f'skirt_b', 
            body['waist'] / 4, 
            body['hips'] / 4,
            body['hips_line'],
            design['length']['v'],
            low_width=design['flare']['v'] * body['hips'] / 4,
            rise=design['rise']['v'],
            dart_position=body['bum_points'] / 2,
            dart_frac=1.1,   
            ruffle=design['ruffle']['v'][1],
            cut=design['back_cut']['v']
        ).translate_to([0, body['waist_level'], -20])

        self.stitching_rules = pyp.Stitches(
            (self.front.interfaces['right'], self.back.interfaces['right']),
            (self.front.interfaces['left'], self.back.interfaces['left'])
        )

        # Reusing interfaces of sub-panels as interfaces of this component
        self.interfaces = {
            'top_f': self.front.interfaces['top'],
            'top_b': self.back.interfaces['top'],
            'top': pyp.Interface.from_multiple(
                self.front.interfaces['top'], self.back.interfaces['top']
            ),
            'bottom': pyp.Interface.from_multiple(
                self.front.interfaces['bottom'], self.back.interfaces['bottom']
            )
        }

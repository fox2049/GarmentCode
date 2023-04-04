"""
    To be used in Python 3.6+ due to dependencies
"""
from copy import copy
import random
import string
import os
import numpy as np

import svgwrite
from svglib import svglib
import svgpathtools as svgpath
from reportlab.graphics import renderPM

import matplotlib.pyplot as plt

# my
import customconfig
from pattern import core

def list_to_c(num):
    """Convert 2D list or list of 2D lists into complex number/list of complex numbers"""
    if isinstance(num[0], list) or isinstance(num[0], np.ndarray):
        return [complex(n[0], n[1]) for n in num]
    else: 
        return complex(num[0], num[1])
    
def c_to_np(num):
    """Convert complex number to a numpy array of 2 elements"""
    return np.asarray([num.real, num.imag])


class VisPattern(core.ParametrizedPattern):
    """
        "Visualizible" pattern wrapper of pattern specification in custom JSON format.
        Input:
            * Pattern template in custom JSON format
        Output representations: 
            * Pattern instance in custom JSON format 
                * In the current state
            * SVG (stitching info is lost)
            * PNG for visualization
        
        Not implemented: 
            * Support for patterns with darts
    """

    # ------------ Interface -------------

    def __init__(self, pattern_file=None, view_ids=True):
        super().__init__(pattern_file)

        # tnx to this all patterns produced from the same template will have the same 
        # visualization scale
        # and that's why I need a class object fot 
        self.scaling_for_drawing = self._verts_to_px_scaling_factor()
        self.view_ids = view_ids  # whatever to render vertices & endes indices

    def serialize(self, path, to_subfolder=True, tag='', with_3d=True, with_text=True):

        log_dir = super().serialize(path, to_subfolder, tag=tag)
        svg_file = os.path.join(log_dir, (self.name + tag + '_pattern.svg'))
        png_file = os.path.join(log_dir, (self.name + tag + '_pattern.png'))
        png_3d_file = os.path.join(log_dir, (self.name + tag + '_3d_pattern.png'))

        # save visualtisation
        self._save_as_image(svg_file, png_file, with_text)
        if with_3d:
            self._save_as_image_3D(png_3d_file)

        return log_dir

    # -------- Drawing ---------

    def _verts_to_px_scaling_factor(self):
        """
        Estimates multiplicative factor to convert vertex units to pixel coordinates
        Heuritic approach, s.t. all the patterns from the same template are displayed similarly
        """
        if len(self.pattern['panels']) == 0:  # empty pattern
            return None
        
        avg_box_x = []
        for panel in self.pattern['panels'].values():
            vertices = np.asarray(panel['vertices'])
            box_size = np.max(vertices, axis=0) - np.min(vertices, axis=0) 
            avg_box_x.append(box_size[0])
        avg_box_x = sum(avg_box_x) / len(avg_box_x)

        if avg_box_x < 2:      # meters
            scaling_to_px = 300
        elif avg_box_x < 200:  # sentimeters
            scaling_to_px = 3
        else:                    # pixels
            scaling_to_px = 1  

        return scaling_to_px

    def _verts_to_px_coords(self, vertices):
        """Convert given to px coordinate frame & units"""
        # Flip Y coordinate (in SVG Y looks down)
        vertices[:, 1] *= -1
        # Put upper left corner of the bounding box at zero
        offset = np.min(vertices, axis=0)
        vertices = vertices - offset
        # Update units scaling
        vertices *= self.scaling_for_drawing
        return vertices

    def _flip_y(self, point):
        """
            To get to image coordinates one might need to flip Y axis
        """
        flipped_point = list(point)  # top-level copy
        flipped_point[1] *= -1
        return flipped_point

    def _draw_a_panel(self, panel_name, offset=[0, 0]):
        """
        Adds a requested panel to the svg drawing with given offset and scaling
        Assumes (!!) 
            that edges are correctly oriented to form a closed loop
        Returns 
            the lower-right vertex coordinate for the convenice of future offsetting.
        """
        attributes = [{
            'fill': 'rgb(216,214,236)',
            'stroke': 'rgb(51,51,51)', 
            'stroke-width': '0.75'
        }]

        panel = self.pattern['panels'][panel_name]
        vertices = np.asarray(panel['vertices'])
        vertices = self._verts_to_px_coords(vertices)
        # Shift vertices for visibility
        vertices = vertices + offset

        # draw edges
        start = vertices[panel['edges'][0]['endpoints'][0]]
        segs = []
        for edge in panel['edges']:
            start = vertices[edge['endpoints'][0]]
            end = vertices[edge['endpoints'][1]]
            if ('curvature' in edge):
                if isinstance(edge['curvature'], list) or edge['curvature']['type'] == 'quadratic':  # FIXME placeholder for old curves
                    control_scale = self._flip_y(edge['curvature'] if isinstance(edge['curvature'], list) else edge['curvature']['params'][0])
                    control_point = self._control_to_abs_coord(
                        start, end, control_scale)
                    segs.append(svgpath.QuadraticBezier(*list_to_c([start, control_point, end])))
                elif edge['curvature']['type'] == 'circle':  # Assuming circle
                    # https://svgwrite.readthedocs.io/en/latest/classes/path.html#svgwrite.path.Path.push_arc

                    radius, large_arc, right = edge['curvature']['params']
                    radius *= self.scaling_for_drawing

                    segs.append(svgpath.Arc(
                        list_to_c(start), radius + 1j*radius,
                        rotation=0,
                        large_arc=large_arc, 
                        sweep=not right,
                        end=list_to_c(end)
                    ))

                    # TODO Support full circle separately (?)
                elif edge['curvature']['type'] == 'cubic':
                    cps = []
                    for p in edge['curvature']['params']:
                        control_scale = self._flip_y(p)
                        control_point = self._control_to_abs_coord(
                            start, end, control_scale)
                        cps.append(control_point)

                    segs.append(svgpath.CubicBezier(*list_to_c([start, *cps, end])))

                else:
                    raise NotImplementedError(f'{self.__class__.__name__}::Unknown curvature type {edge["curvature"]["type"]}')

            else:
                segs.append(svgpath.Line(*list_to_c([start, end])))
        
        max_x = np.max(vertices[:, 0])

        return svgpath.Path(*segs), attributes, max_x

    def _add_panel_annotations(
            self, drawing, panel_name, path:svgpath.Path, offset=[0, 0], with_text=True, view_ids=True):
        """ Adds a annotations for requested panel to the svg drawing with given offset and scaling
        Assumes (!!) 
            that edges are correctly oriented to form a closed loop
        Returns 
            the lower-right vertex coordinate for the convenice of future offsetting.
        """
        panel = self.pattern['panels'][panel_name]
        vertices = np.asarray(panel['vertices'])
        vertices = self._verts_to_px_coords(vertices)
        # Shift vertices for visibility
        vertices = vertices + offset

        bbox = path.bbox()
        panel_center = np.array([(bbox[0] + bbox[1]) / 2, (bbox[2] + bbox[3]) / 2])
        
        if with_text:
            text_insert = panel_center   # + np.array([-len(panel_name) * 12 / 2, 3])
            drawing.add(drawing.text(panel_name, insert=text_insert, 
                        fill='rgb(31,31,31)', font_size='25', 
                        text_anchor='middle', dominant_baseline='middle'))

        if view_ids:
            # name vertices 
            # TODO Use path informaiton for placing vertex ids => no need for offset
            for idx in range(vertices.shape[0]):
                shift = vertices[idx] - panel_center
                # last element moves pivot to digit center
                shift = 5 * shift / np.linalg.norm(shift) + np.array([-5, 5])
                drawing.add(
                    drawing.text(str(idx), insert=vertices[idx] + shift, 
                                 fill='rgb(245,96,66)', font_size='25'))
            # name edges
            for idx in range(len(path)):
                seg = path[idx]
                middle = c_to_np(seg.point(seg.ilength(seg.length() / 2)))
                middle[1] -= 3  # slightly above the line
                # name
                drawing.add(
                    drawing.text(idx, insert=middle, 
                                 fill='rgb(44,131,68)', font_size='20', 
                                 text_anchor='middle'))


    def _save_as_image(self, svg_filename, png_filename, with_text=True):
        """
            Saves current pattern in svg and png format for visualization
        """
        if self.scaling_for_drawing is None:  # re-evaluate if not ready
            self.scaling_for_drawing = self._verts_to_px_scaling_factor()

        base_offset = [60, 60]
        panel_offset_x = 0

        panel_order = self.panel_order()
        paths = []
        attributes = []
        offsets = [0]
        for panel in panel_order:
            if panel is not None:
                path, attr, panel_offset_x = self._draw_a_panel(
                    panel,
                    offset=[panel_offset_x + base_offset[0], base_offset[1]], 
                )
                paths.append(path)
                attributes += attr
                offsets.append(panel_offset_x)

        # SVG convert
        dwg = svgpath.wsvg(paths, attributes=attributes, 
                     filename=svg_filename, 
                     paths2Drawing=True)

        # text annotations
        if with_text or self.view_ids:
            for i, panel in enumerate(panel_order):
                if panel is not None:
                    self._add_panel_annotations(
                        dwg, panel, paths[i],
                        [offsets[i] + base_offset[0], base_offset[1]], 
                        with_text, self.view_ids)
        
        dwg.save(pretty=True)

        # to png
        svg_pattern = svglib.svg2rlg(svg_filename)
        renderPM.drawToFile(svg_pattern, png_filename, fmt='PNG')

    def _save_as_image_3D(self, png_filename):
        """Save the patterns with 3D positioning using matplotlib visualization"""

        fig = plt.figure(figsize=(30 / 2.54, 30 / 2.54))
        ax = fig.add_subplot(projection='3d')


        # TODO Support arcs / curves
        for panel in self.pattern['panels']:
            p = self.pattern['panels'][panel]
            rot = p['rotation']
            tr = p['translation']
            verts_2d = p['vertices']

            verts_to_plot = copy(verts_2d)
            verts_to_plot.append(verts_to_plot[0])

            verts3d = np.vstack(tuple([self._point_in_3D(v, rot, tr) for v in verts_to_plot]))
            x = np.squeeze(np.asarray(verts3d[:, 0]))
            y = np.squeeze(np.asarray(verts3d[:, 1]))
            z = np.squeeze(np.asarray(verts3d[:, 2]))

            ax.plot(x, y, z)

        ax.view_init(elev=115, azim=-59, roll=30)
        ax.set_aspect('equal')
        fig.savefig(png_filename, dpi=300, transparent=False)
        # DEBUG plt.show()


class RandomPattern(VisPattern):
    """
        Parameter randomization of a pattern template in custom JSON format.
        Input:
            * Pattern template in custom JSON format
        Output representations: 
            * Pattern instance in custom JSON format 
                (with updated parameter values and vertex positions)
            * SVG (stitching info is lost)
            * PNG for visualization

        Implementation limitations: 
            * Parameter randomization is only performed once on loading
            * Only accepts unchanged template files (all parameter values = 1) 
            otherwise, parameter values will go out of control and outside of the original range
            (with no way to recognise it)
    """

    # ------------ Interface -------------
    def __init__(self, template_file):
        """Note that this class requires some input file: 
            there is not point of creating this object with empty pattern"""
        super().__init__(template_file, view_ids=False)  # don't show ids for datasets

        # update name for a random pattern
        self.name = self.name + '_' + self._id_generator()

        # randomization setup
        self._randomize_pattern()

    # -------- Other Utils ---------
    def _id_generator(self, size=10,
                      chars=string.ascii_uppercase + string.digits):
        """Generated a random string of a given size, see
        https://stackoverflow.com/questions/2257441/random-string-generation-with-upper-case-letters-and-digits
        """
        return ''.join(random.choices(chars, k=size))


if __name__ == "__main__":
    from datetime import datetime
    import time

    timestamp = int(time.time())
    random.seed(timestamp)

    system_config = customconfig.Properties('./system.json')
    base_path = system_config['output']
    # pattern = VisPattern(os.path.join(system_config['templates_path'], 'skirts', 'skirt_4_panels.json'))
    # pattern = VisPattern(os.path.join(system_config['templates_path'], 'basic tee', 'tee.json'))
    pattern = VisPattern(os.path.join(
        base_path, 
        'nn_pred_data_1000_tee_200527-14-50-42_regen_200612-16-56-43200803-10-10-41', 
        'test', 'tee_00A2ZO1ELB', '_predicted_specification.json'))
    # newpattern = RandomPattern(os.path.join(system_config['templates_path'], 'basic tee', 'tee.json'))

    # log to file
    log_folder = 'panel_vissize_' + datetime.now().strftime('%y%m%d-%H-%M-%S')
    log_folder = os.path.join(base_path, log_folder)
    os.makedirs(log_folder)

    pattern.serialize(log_folder, to_subfolder=False)
    # newpattern.serialize(log_folder, to_subfolder=False)

    # log random seed
    with open(log_folder + '/random_seed.txt', 'w') as f_rand:
        f_rand.write(str(timestamp))

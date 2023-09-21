import os
import mujoco
import mujoco.viewer as viewer
from mujoco.usd_component import *
from mujoco.usd_utilities import *
from pxr import Usd, UsdGeom

from PIL import Image as im
from PIL import ImageOps

class USDRenderer(object):
  """
  Renderer class the creates USD representations for mujoco scenes
  """
  def __init__(self,
               model,
               height=480,
               width=480):
    self.model = model
    self.data = None
    self.renderer = mujoco.Renderer(model, height, width)

    self.loaded_scene_info = False

    self.stage = Usd.Stage.CreateNew('usd_stage.usda')
    UsdGeom.SetStageUpAxis(self.stage, UsdGeom.Tokens.z)

  @property
  def usd(self):
    return self.stage.GetRootLayer().ExportToString()
  
  @property
  def scene(self):
    return self.renderer.scene
  
  def save_scene(self):
    self.stage.GetRootLayer().Save()

  def update_scene(self, data):
    self.renderer.update_scene(data)
    self.data = data

    if not self.loaded_scene_info:
      # loads the initial geoms, lights, and camera information 
      # from the scene
      self._load()
      self.loaded_scene_info = True
    
    self._update()

  def _load(self):
    """
    Loads and initializes the necessary objects to render the scene
    """

    # TODO: remove these and replace by reading directly from model
    # if self.model.nmesh > 0:
    #   mesh_vertex_ranges = get_mesh_ranges(self.model.nmesh, self.model.mesh_vertnum)
    #   mesh_face_ranges = get_mesh_ranges(self.model.nmesh, self.model.mesh_facenum)
    #   mesh_texcoord_ranges = get_mesh_ranges(self.model.nmesh, self.model.mesh_texcoordnum)
    #   mesh_facetexcoord_ranges = get_facetexcoord_ranges(self.model.nmesh, self.model.mesh_facenum)

    # create and load the texture files
    # iterate through all the textures and build list of tex_rgb ranges
    data_adr = 0
    texture_files = []
    for texid in range(self.model.ntex):
      height = self.model.tex_height[texid]
      width = self.model.tex_width[texid]
      pixels = 3*height*width
      rgb = self.model.tex_rgb[data_adr:data_adr+pixels]
      img = rgb.reshape(height, width, 3)
      file_name = f'{texid}.png'
      img = im.fromarray(img)
      img = ImageOps.flip(img)
      img.save(file_name)
      texture_file = os.path.abspath(file_name)
      texture_files.append(texture_file)
      data_adr += pixels

    # initializes an array to store all the geoms in the scene
    # populates with "empty" USDGeom objects
    self.usd_geoms = []
    geoms = self.scene.geoms
    self.ngeom = self.scene.ngeom
    for i in range(self.ngeom):
      geom = geoms[i]
      if geom.category == 1:
        self.usd_geoms.append(None)
        continue
      if geom.texid == -1:
        texture_file = None
      else:
        texture_file = texture_files[geom.texid]

      if geom.type == USDGeomType.Mesh.value:
        self.usd_geoms.append(USDMesh(self.model.geom_dataid[i],
                                      geom, 
                                      self.stage, 
                                      self.model,
                                      texture_file))
      else:
        self.usd_geoms.append(create_usd_geom_primitive(geom, 
                                                        self.stage,
                                                        texture_file))

    # initializes an array to store all the lights in the scene
    # populates with "empty" USDLight objects
    self.usd_lights = []
    lights = self.scene.lights
    self.nlight = self.scene.nlight
    for i in range(self.nlight):
      self.usd_lights.append(USDLight(self.stage))

  def _update(self):
    self._update_geoms()
    self._update_lights()
    self._update_camera()

  def _update_geoms(self):
    """
    Updates the geoms to match the current scene
    """
    geoms = self.scene.geoms
    for i in range(self.ngeom):
      if self.usd_geoms[i] != None: # TODO: remove this once all primitives are added
        self.usd_geoms[i].update_geom(geoms[i])

  def _update_lights(self):
    """
    Updates the lights to match the current scene
    """
    lights = self.scene.lights
    nlight = self.scene.nlight
    for i in range(nlight):
      self.usd_lights[i].update_light(lights[i])
      
  def _update_camera(self):
    """
    Updates the camera to match the current scene
    """
    pass

  def start_viewer(self):
    if self.data:
      viewer.launch(self.model)

  def render(self):
    # should render the usd file given a particular renderer that
    # works with USD files
    # TODO: determine if this is valid functionality
    pass

  # TODO: remove later, this is only for debugging purposes
  def print_geom_information(self):
    for i in range(self.ngeom):
      print(self.usd_geoms[i])
from __future__ import absolute_import, division, print_function
from iotbx.map_model_manager import map_model_manager
from iotbx.data_manager import DataManager
from cctbx.maptbx.prepare_map_for_docking import mask_fixed_model_region
from cctbx.maptbx.prepare_map_for_docking import assess_cryoem_errors
from cctbx.maptbx.prepare_map_for_docking import sphere_enclosing_model
dm = DataManager()
dm.set_overwrite(True)

def prepare_map_for_refinement(map1_filename, map2_filename, d_min,
            working_model_filename, fixed_model_filename=None, verbosity=1):

  working_model = dm.get_model(working_model_filename)
  sphere_cent, radius = sphere_enclosing_model(working_model)
  radius = radius + d_min # Expand to allow width for density

  # Create map_model_manager containing half-maps
  mm1 = dm.get_real_map(map1_filename)
  mm2 = dm.get_real_map(map2_filename)
  mmm = map_model_manager(map_manager_1=mm1, map_manager_2=mm2)

  if fixed_model_filename is not None:
    fixed_model = dm.get_model(fixed_model_filename)
    mmm.add_model_by_id(model=fixed_model, model_id='fixed_model')
    mmm.generate_map(model=fixed_model, d_min=d_min, map_id='fixed_atom_map')

  ordered_mask_id = None
  # ordered_mask_id = 'ordered_volume_mask'
  # add_ordered_volume_mask(mmm, d_min,
  #     protein_mw=protein_mw, nucleic_mw=nucleic_mw,
  #     ordered_mask_id=ordered_mask_id)

  fixed_mask_id = None
  if fixed_model_filename is not None:
    fixed_mask_id = 'mask_around_atoms'
    mask_fixed_model_region(mmm, d_min,
                            fixed_model=fixed_model,
                            ordered_mask_id=ordered_mask_id,
                            fixed_mask_id=fixed_mask_id)

  # Refine to get scale and error parameters for docking region
  results = assess_cryoem_errors(mmm, d_min,
    determine_ordered_volume=False, verbosity=verbosity,
    sphere_cent=sphere_cent, radius=radius,
    ordered_mask_id=ordered_mask_id, fixed_mask_id=fixed_mask_id)

  return results

def run():
  """
  Prepare cryo-EM map for refinement of portion in context by preparing weighted MTZ file.

  Obligatory command-line arguments (no keywords):
  half_map_1: name of file containing the first half-map from a reconstruction
  half_map_2: name of file containing the second half-map
  working_model: Model file for placed working model that will be refined
  d_min: local resolution of map around working model

  Optional command-line arguments (keyworded):
  --fixed_model: Model file for fixed model that partly explains rest of map
  --file_root: root name for output files
  --mute (or -m): mute output
  --verbose (or -v): verbose output
  --testing: extra verbose output for debugging
  """
  import argparse
  parser = argparse.ArgumentParser(
          description='Prepare cryo-EM map for refinement')
  parser.add_argument('map1', help='Map file for half-map 1')
  parser.add_argument('map2', help='Map file for half-map 2')
  parser.add_argument('working_model',
                      help='Model for portion that will be refined')
  parser.add_argument('d_min', help='local resolution', type=float)
  parser.add_argument('--fixed_model',
                      help='Optional fixed model accounting for explained map features')
  parser.add_argument('--file_root',
                      help='Root of filenames for output')
  parser.add_argument('-m', '--mute', help = 'Mute output', action = 'store_true')
  parser.add_argument('-v', '--verbose', help = 'Set output as verbose',
                      action = 'store_true')
  parser.add_argument('--testing', help='Set output as testing level', action='store_true')

  args = parser.parse_args()
  map1_filename = args.map1
  map2_filename = args.map2
  d_min = args.d_min

  # Verbosity levels: 0=mute, logfile=1, verbose=2, testing=4
  verbosity = 1
  if args.mute: verbosity = 0
  if args.verbose: verbosity = 2
  if args.testing: verbosity = 4
  working_model_filename = args.working_model
  fixed_model_filename = args.fixed_model

  results = prepare_map_for_refinement(map1_filename, map2_filename, d_min,
            working_model_filename, fixed_model_filename=fixed_model_filename,
            verbosity=verbosity)

  expectE = results.expectE
  mtz_dataset = expectE.as_mtz_dataset(column_root_label='Emean')
  dobs = results.dobs
  mtz_dataset.add_miller_array(
      dobs,column_root_label='Dobs',column_types='W')
  mtz_object=mtz_dataset.mtz_object()

  if args.file_root is not None:
    mtzout_file_name = args.file_root + ".mtz"
    mapout_file_name = args.file_root + "_likelihood_weighted.map"
  else:
    mtzout_file_name = "weighted_map_data.mtz"
    mapout_file_name = "likelihood_weighted.map"
  print ("Writing mtz for refinement as", mtzout_file_name)
  dm.write_miller_array_file(mtz_object, filename=mtzout_file_name)
  print ("Writing likelihood-weighted map as", mapout_file_name)
  new_mmm = results.new_mmm
  new_mmm.write_map(map_id='map_manager_lwtd', file_name = mapout_file_name)

if __name__ == "__main__":
  run()

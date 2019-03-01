'''
	prelim_analysis.py

	isolates the region of the model that we actually want to look at by 
	1. mapping the all_results mesh onto the initial model that was used to generate it 
	2. extracting the region that was defined as the aneurysm
	3. clipping that region out of the all_results.vtp into its own file 

	this facilitates analysis that will be performed on the clipped_result file. for each 
	extracted aneurysm, we can do:
	ACTUALLY we probably want the centerline points, axialref/thetaref and correspondences from the mapping for this step
	so that eventually, we can unfold the aneurysm into patches and take advantage of spatial correspondences in our analysis 
	1. determine the distribution of tawss (ptp, min, max, CI)
	2. determine the distribution of tawss (%area at continuous cutoff)
'''

# external dependencies
import numpy as np
import vtk
from vtk.util import numpy_support as nps	
import sys
import os
import argparse
from tqdm import tqdm

# internal modules
from AneurysmGeneration.utils.batch import *
from AneurysmGeneration.utils.normalization import *
from AneurysmGeneration.utils.slice import *


def parse_command_line(args):
	'''

	'''
	
	print 'parsing command line'

	parser = argparse.ArgumentParser(description='Integrated pipeline for processing simulation result including \
												with mapping, clipping to extract aneurysm regions from .vtp; also \
												supports clipping of associated .vtu file')
	parser.add_argument('--source', 
						action="store", 
						type=str, 
						default="AneurysmGeneration/models/SKD0050/SKD0050_baseline_model_modified_p1.vtp"
						)
	parser.add_argument('--results', 
						action="store", 
						type=str, 
						default="Artificial/RCA/p1/all_results.vtp"
						)
	parser.add_argument('--outdir', 
						action="store", 
						type=str, 
						default='clipped_results_short/'
						)
	parser.add_argument('--baseline_dir', 
						action="store",
					    type=str,
					    default='Artificial/baseline/all_results.vtu',
					    )
	parser.add_argument('--pkl', 
						dest='pkl', 
						action='store_true'
						)
	parser.add_argument('--vtk', 
						dest='vtk',
						action='store_true'
						)
	parser.add_argument('--vtu', 
						dest='vtu',
						action='store_true'
						)
	parser.add_argument('--baseline', 
					    dest='baseline',
					    action='store_true',
					    )
	parser.add_argument('--mapping', 
						dest='mapping', 
						action='store_true'
						)
	parser.add_argument('--debug', 
						dest='debug', 
						action='store_true'
						)
	parser.add_argument('--post', 
						dest='post', 
						action='store_true'
						)
	parser.add_argument('--clip', 
						dest='clip', 
						action='store_true'
						)
	parser.add_argument('--suff', 
						action="store", 
						type=str, 
						default='p1'
						)
	parser.add_argument('--shape',
						action="store",
						type=str,
						default='ASI2')

	args = vars(parser.parse_args())

	return args


def apply_bounding_box(centerline, points, offsets=np.array([.11, .15, .8])):
	'''
		apply a bounding box based on min/max in axis 0 of centerline to points, 
		return the restricted indices
		Apply some offsets to each direction so that we definitely get all the points that we're looking for 

	'''

	print 'applying bb'

	upperbounds = np.amax(centerline, axis=0) + offsets
	lowerbounds = np.amin(centerline, axis=0) - offsets
	first = np.all(np.greater_equal(points, lowerbounds), axis=1)
	print first 

	inner = np.logical_and(
			np.all(np.greater_equal(points, lowerbounds), axis=1), 
			np.all(np.less_equal(points, upperbounds), axis=1) 
			)
	print inner
	patch_index = np.where(
		np.logical_and(
			np.all(np.greater_equal(points, lowerbounds), axis=1), 
			np.all(np.less_equal(points, upperbounds), axis=1) 
			) 
		)

	return patch_index


def get_points(source_model_path, all_results_path, suff): 
	"""Summary
	
	Args:
	    source_model_path (TYPE): Description
	    all_results_path (TYPE): Description
	    suff (TYPE): Description
	
	Returns:
	    TYPE: Description
	"""
	# we need to get the source models
	poly_source = return_polydata(source_model_path)

	# we need the all_results_mesh
	poly_results = return_polydata(all_results_path)

	# for debugging/testing purposes
	gNid_array = nps.vtk_to_numpy(poly_results.GetPointData().GetArray('GlobalNodeID'))
	print 'the gnid array has shape', gNid_array.shape

	# extract the raw points from the polydata
	_, points_source = extract_points(poly_source)
	_, points_results = extract_points(poly_results)

	write_to_file('points_' + suff, (points_source, points_results))

	return points_source, points_results


def compute_mapping(centerline, points_source, points_results, correct_face, suff, block_sz=150, save_to_disk=False): 
	"""Summary
	
	Args:
	    centerline (TYPE): Description
	    points_source (TYPE): Description
	    points_results (TYPE): Description
	    correct_face (TYPE): Description
	    suff (TYPE): Description
	    block_sz (int, optional): Description
	    save_to_disk (bool, optional): Description
	
	Returns:
	    TYPE: Description
	"""
	# use the centerline to apply a bounding box to the points that we need to look at 
	bounded_source_idx = apply_bounding_box(centerline, points_source)[0]
	bounded_results_idx = apply_bounding_box(centerline, points_results)[0]

	mapping = np.zeros(points_results.shape[0])

	# chunk one of the arrays so that we don't run out of memory when we 
	# perform the vectorized distance computation
	n_splits = len(bounded_results_idx)//100

	for i in tqdm(range(n_splits), desc='splitting mapping computation', file=sys.stdout):

		cur_idx = bounded_results_idx[block_sz*i:block_sz*(i+1)]

		if i == n_splits - 1:
			cur_idx = bounded_results_idx[block_sz*i:]

		mapping[cur_idx], _ = minimize_distances(points_results[cur_idx], points_source)

	write_to_file('mapping_'+suff, mapping)

	vessel_ids = []
	mapped = np.zeros(mapping.shape[0])

	for c, cand in enumerate(mapping):
		if cand in correct_face:
			mapped[c] = 1
			vessel_ids.append(c)

	vessel_points = points_results[vessel_ids]

	if save_to_disk: write_to_file('mapped_'+ suff, (vessel_ids, vessel_points))

	return vessel_ids, vessel_points


def post_process_clip(centerline, points_results, poly_results, 
					vessel_ids, vessel_points, 
					start, length, NoP, 
					outdir, 
					suff,
					save_to_disk, 
					save_parameters=True): 
	"""Summary
	
	Args:
	    centerline (TYPE): Description
	    points_results (TYPE): Description
	    poly_results (TYPE): Description
	    vessel_ids (TYPE): Description
	    vessel_points (TYPE): Description
	    start (TYPE): Description
	    length (TYPE): Description
	    NoP (TYPE): Description
	    fname_out (TYPE): Description
	    save_to_disk (TYPE): Description
	    save_parameters (bool, optional): Description
	
	Returns:
	    tuple: Description
	"""
	print 'doing post_process_clip routine'

	# use normalization utils to map mesh points onto the centerline
	wall_ref, _, _, _, centerline_length = projection(NoP, centerline, points_results, vessel_ids)

	end = start+length/centerline_length

	wall_region, axial_pos, theta_pos, start_id, end_id = obtain_expansion_region(wall_ref, NoP, vessel_ids, start=start, end=end)

	# ------------- isolate clipping boundaries -------------------
	points_start = extract_points(poly_results, start_id)
	points_end = extract_points(poly_results, end_id)

	# ------------- prepare clipping planes -------------------
	# a single clip plane is defined by an origin and a normal, origin computed as the average position of a ring of points 
	origin_start = np.mean(points_start, axis=0)
	origin_end = np.mean(points_end, axis=0)

	# print origin_start
	# print origin_end

	# span, that we can use to ensure that the normals face in the right direction
	span = origin_end - origin_start
	span /= np.linalg.norm(span)

	# print span

	# shift the origin by a bit 
	alpha = .02
	origin_start += span*alpha
	origin_end -= span*alpha

	# define planes
	plane_start = vtk.vtkPlane()
	plane_start.SetOrigin(origin_start)
	plane_start.SetNormal(-1*span)

	plane_end = vtk.vtkPlane()
	plane_end.SetOrigin(origin_end)
	plane_end.SetNormal(span)

	# ------------- clipping in action -------------------
	# now let's pipe the two geometry extractors
	extract_start = vtk.vtkExtractPolyDataGeometry()
	extract_start.SetInputData(poly_results)
	extract_start.SetImplicitFunction(plane_start)
	extract_start.SetExtractBoundaryCells(True)
	extract_start.PassPointsOn()
	extract_start.Update()

	extract_end = vtk.vtkExtractPolyDataGeometry()
	extract_end.SetInputConnection(extract_start.GetOutputPort())
	extract_end.SetImplicitFunction(plane_end)
	extract_end.SetExtractBoundaryCells(True)
	extract_end.PassPointsOn()
	extract_end.Update()

	# ------------- connectivity to make sure we're extracting correctly -------------------
	connect = vtk.vtkPolyDataConnectivityFilter()
	connect.SetInputData(extract_end.GetOutput())
	connect.SetExtractionModeToLargestRegion()
	connect.Update()

	region = connect.GetOutput()

	print 'output region has NoP:', region.GetNumberOfPoints()

	# ------------- write the new clipped region to disk -------------------
	if save_to_disk: 
		clipped_writer = vtk.vtkXMLPolyDataWriter()
		clipped_writer.SetInputData(region)
		clipped_writer.SetFileName(outdir + suff + '.vtp')
		clipped_writer.Write()

	if save_parameters:
		write_to_file(suff + '_parameters', (origin_start, origin_end, span))

	print 'completed post_process_clip routine'

	return (origin_start, origin_end, span)


def clip_vtu(clip_parameters, fname_out, unstructured_results): 
	"""Summary
	
	Args:
	    clip_parameter_loc (TYPE): Description
	    fname_out (TYPE): Description
	    unstructured_results (TYPE): Description
	
	"""
	print 'doing clip_vtu routine'

	if isinstance(clip_parameters, str): 
		origin_start, origin_end, span = read_from_file(clip_parameters)
	else: 
		origin_start, origin_end, span = clip_parameters

	# define planes
	plane_start = vtk.vtkPlane()
	plane_start.SetOrigin(origin_start)
	plane_start.SetNormal(-1*span)

	plane_end = vtk.vtkPlane()
	plane_end.SetOrigin(origin_end)
	plane_end.SetNormal(span)

	extract_start = vtk.vtkExtractGeometry()
	extract_start.SetInputData(unstructured_results)
	extract_start.SetImplicitFunction(plane_start)
	extract_start.SetExtractBoundaryCells(True)
	extract_start.Update()

	extract_end = vtk.vtkExtractGeometry()
	extract_end.SetInputData(extract_start.GetOutput())
	extract_end.SetImplicitFunction(plane_end)
	extract_end.SetExtractBoundaryCells(True)
	extract_end.Update()

	connect = vtk.vtkConnectivityFilter()
	connect.SetInputConnection(extract_end.GetOutputPort())
	connect.SetExtractionModeToLargestRegion()
	connect.Update()

	region = connect.GetOutput()

	print region.GetNumberOfPoints()

	clipped_writer = vtk.vtkXMLUnstructuredGridWriter()
	clipped_writer.SetInputData(region)
	clipped_writer.SetFileName(fname_out + '.vtu')
	clipped_writer.Write()

	print 'completed clip_vtu routine'


def main():

	args = parse_command_line(sys.argv)

	print args['baseline_dir']

	# we need the face to points correspondence from the original source model 
	# we only need to get this once 
	(face_to_points, _, _, NoP) = read_from_file("big_boy")

	points_source = None
	points_results = None
	centerline = None
	vessel_ids = None
	vessel_points = None
	faceID = 0

	# get start and length from targets 
	targets = collect_target_dictionary(side='R')
	cl_choice, start, length, _ = targets[args['shape']][args['suff']]

	if cl_choice == 2: 
		centerline = read_from_file('RCA_cl')
		faceID = 8
	else: 
		centerline = read_from_file('centerlines')[cl_choice]
		faceID = 2

	if args['vtk']: 
		points_source, points_results = get_points(args['source'], args['results'], args['suff'])

	elif args['pkl']:
		points_source, points_results = read_from_file('points_' + args['suff'])

	if args['mapping']:
		vessel_ids, vessel_points = compute_mapping(centerline, points_source, points_results, face_to_points[faceID], args['suff'], save_to_disk=True)

	if args['post']:

		all_results_path = args['results']

		poly_results = return_polydata(all_results_path)

		if vessel_ids is None or vessel_points is None: 
			vessel_ids, vessel_points = read_from_file('mapped_'+args['suff'])

		clip_parameters = post_process_clip(centerline, 
											points_results, 
											poly_results, 
											vessel_ids, 
											vessel_points, 
											start, 
											length, 
											NoP,
											args['outdir'], 
											args['suff'],
											save_to_disk=True)
					
		if args['baseline']	: 
			unstructured_results = return_unstructured(args['baseline_dir'])
			clip_vtu(clip_parameters, args['outdir'] + 'baseline_' + args['shape'] + '_' + args['suff'], unstructured_results)

		elif args['vtu']: 
			unstructured_results = return_unstructured(args['results'][:-3] + 'vtu') 
			clip_vtu(clip_parameters, args['outdir'] + args['suff'], unstructured_results)


if __name__ == "__main__":
	main()




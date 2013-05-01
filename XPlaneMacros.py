#
# Copyright (c) 2012-2013 Ben Supnik
#
# This code is licensed under version 2 of the GNU General Public License.
# http://www.gnu.org/licenses/gpl-2.0.html
#
# See ReadMe-XPlane2Blender.html for usage.
#

road_matches = [
    ['local_cores', "io 50 io 51 io 52 io 53 io 54 io 55 io 56 io 57 io 58 io 60 io 61 io 62 io 63 io 64 io 66 io 66 io 67 io 68"],

    ['local_cores_in', "in 50 in 51 in 52 in 53 in 54 in 55 in 56 in 57 in 58 in 60 in 61 in 62 in 63 in 64 in 66 in 66 in 67 in 68"],

    ['primary_cores', "io 10 io 11 io 12 io 13 io 14 io 15 io 16 io 17 io 18"],

    ['secondary_cores_twoway', "io 30 io 31 io 32 io 33 io 34 io 35 io 36 io 37 io 38"],

    ['secondary_cores_all', "io 30 io 31 io 32 io 33 io 34 io 35 io 36 io 37 io 38 io 40 io 41 io 42 io 43 io 44 io 45 io 46 io 47 io 48"],

    ['secondary_cores_in', "in 30 in 31 in 32 in 33 in 34 in 35 in 36 in 37 in 38"],

    ['secondary_cores_out', "out 30 out 31 out 32 out 33 out 34 out 35 out 36 out 37 out 38"],


    ['secondary_cores_oneway_in', "in 40 in 41 in 42 in 43 in 44 in 45 in 46 in 47 in 48"],

    ['secondary_cores_oneway_out', "out 40 out 41 out 42 out 43 out 44 out 45 out 46 out 47 out 48"],

    ['left_ww',
    "in 12 in 15 out 16 out 17 io 18 "
    "in 22 in 25 out 26 out 27 io 28 "
    "in 32 in 35 out 36 out 37 io 38 "
    "in 42 in 45 out 46 out 47 io 48 "
    "in 52 in 55 out 56 out 57 io 58 "
    "in 62 in 65 out 66 out 67 io 68 "],
    ['right_ww',
    "in 16 in 17 out 12 out 15 io 18 "
    "in 26 in 27 out 22 out 25 io 28 "
    "in 36 in 37 out 32 out 35 io 38 "
    "in 46 in 47 out 42 out 45 io 48 "
    "in 56 in 57 out 52 out 55 io 58 "
    "in 66 in 67 out 62 out 65 io 68 "],

    ['left_sw',
    "in 11 in 17 out 13 out 15 io 14 "
    "in 21 in 27 out 23 out 25 io 24 "
    "in 31 in 37 out 33 out 35 io 34 "
    "in 41 in 47 out 43 out 45 io 44 "
    "in 51 in 57 out 53 out 55 io 54 "
    "in 61 in 67 out 63 out 65 io 64 "],

    ['right_sw',
    "out 11 out 17 in 13 in 15 io 14 "
    "out 21 out 27 in 23 in 25 io 24 "
    "out 31 out 37 in 33 in 35 io 34 "
    "out 41 out 47 in 43 in 45 io 44 "
    "out 51 out 57 in 53 in 55 io 54 "
    "out 61 out 67 in 63 in 65 io 64 "],

    ['left_AO',
    "in 13 in 16 out 11 out 12 io 10 "
    "in 23 in 26 out 21 out 22 io 20 "
    "in 33 in 36 out 31 out 32 io 30 "
    "in 43 in 46 out 41 out 42 io 40 "
    "in 53 in 56 out 51 out 52 io 50 "
    "in 63 in 66 out 61 out 62 io 60 "
    "io 120 io 121"],

    ['right_AO',
    "in 16 in 13 out 12 out 11  io 10 "
    "in 26 in 23 out 22 out 21  io 20 "
    "in 36 in 33 out 32 out 31  io 30 "
    "in 46 in 43 out 42 out 41  io 40 "
    "in 56 in 53 out 52 out 51  io 50 "
    "in 66 in 63 out 62 out 61  io 60 "
    "io 120 io 121"],

    ['right_AO_sw_ww',
    "io 10 io 11 io 12 io 13 io 14 io 15 io 16 io 17 io 18 io 20 io 21 io 22 io 23 io 24 io 25 io 26 io 27 io 28 "
    "io 30 io 31 io 32 io 33 io 34 io 35 io 36 io 37 io 38 io 40 io 41 io 42 io 43 io 44 io 45 io 46 io 47 io 48 "
    "io 50 io 51 io 52 io 53 io 54 io 55 io 56 io 57 io 58 io 60 io 61 io 62 io 63 io 64 io 65 io 66 io 67 io 68 "
    "io 120 io 121"],

    ['left_AO_sw_ww',
    "io 10 io 11 io 12 io 13 io 14 io 15 io 16 io 17 io 18 io 20 io 21 io 22 io 23 io 24 io 25 io 26 io 27 io 28 "
    "io 30 io 31 io 32 io 33 io 34 io 35 io 36 io 37 io 38 io 40 io 41 io 42 io 43 io 44 io 45 io 46 io 47 io 48 "
    "io 50 io 51 io 52 io 53 io 54 io 55 io 56 io 57 io 58 io 60 io 61 io 62 io 63 io 64 io 65 io 66 io 67 io 68 "
    "io 120 io 121"	],

    ['primary_or_secondary_right_ww',
    "in 16 in 17 in 18 "
    "in 26 in 27 in 28 "
    "in 36 in 37 in 38 "
    "in 46 in 47 in 48 "],


#  SW pri LH:	in 11 io 14 in 17 out 13 out 15  out 23 out 24 out 25

#  AO pri LH:	in 13 io 10 in 16 out 11 out 12  out 20 out 21 out 22
#  SW pri RH:	in 13 io 14 in 15 out 11 out 17  in  23 in 24 in 25
#	out 21 out 24 out 27 out 41 out 44 out 47 out 61 out 64 out 67
#   out 20 out 23 out 26 out 40 out 43 out 46 out 60 out 63 out 66
#	in 51 in 52 io 50 out 53 out 56 in 60 in 61 in 62 in 31 in 32 io 30 out 33 out 36 in 40 in 41 in 42

#	in 32 in 35 io 38 out 36 out 37
#	in 56 in 57 io 58 out 52 out 55  in 36 in 37 io 38 out 32 out 35

#	in 12 in 15  out 16 out 17 io 18  out 26 out 27 out 28
#	in 16 in 17 io 18 out 12 out 15   in 26 in 27 in 28   in 46 in 47 in 48 in 66 in 67 in 68

#	out 22 out 25 out 28 out 42 out 45 out 48 out 62 out 65 out 68
#	in 56 in 57 io 58 out 52 out 55 in 66 in 67 in 68 in 36 in 37 io 38 out 32 out 35 in 46 in 47 in 48

#   in 16 in 17 out 12 out 15 io 18 in 26 in 27 out 22 out 25 io 28 in 36 in 37 out 32 out 35 io 38 in 46 in 47 out 42 out 45 io 48
#   in 12 in 15 out 16 out 17 io 18 in 22 in 25 out 26 out 27 io 28 in 32 in 35 out 36 out 37 io 38 in 42 in 45 out 46 out 47 io 48


    ['any_train', "io 151 io 152 io 153"]
]

macros = [
    ['WetGrassGravel1',
        "TEXTURE_DETAIL 4 4 ../../common_textures/detail/grass_and_asphalt_DTL.png\n"
        "TEXTURE_TERRAIN 180 180 ../../common_textures/ground/grass_wet_patchy_TRN.png\n"],

    ['TILE_LOD_15000',
        "TILE_LOD  15000\n"],

    ['TILE_LOD_30000',
        "TILE_LOD  30000\n"],

    ['AGS_suburban_garden_1',
        "DECAL_LIB   lib/g10/decals/AGS_suburban_garden_1.dcl\n"
        "TEXTURE_TERRAIN 180 180 ../../common_textures/ground/grass_wet_patchy_TRN.png\n"
        "TILE_LOD  20000\n"],

    ['AGS_suburban_garden_2',
        "DECAL_LIB   lib/g10/decals/AGS_suburban_garden_1.dcl\n"
        "TEXTURE_TERRAIN 180 180 ../../common_textures/ground/lawn_collage_TRN.png\n"
        "TILE_LOD  20000\n"],

    ['sub_gdn_wet',
        "DECAL_LIB   lib/g10/decals/AGS_suburban_garden_1.dcl\n"
        "TEXTURE_TERRAIN 180 180 ../../common_textures/ground/grass_wet_patchy_TRN.png\n"
        "TILE_LOD  20000\n"],

    ['sub_gdn',
        "DECAL_LIB   lib/g10/decals/AGS_suburban_garden_1.dcl\n"
        "TEXTURE_TERRAIN 200 200 ../../common_textures/ground/grass_wet_patchy_TRN.png\n"
        "TILE_LOD  20000\n"],

    ['sub_gdn_wet_alt',
        "DECAL_LIB   lib/g10/decals/AGS_suburban_garden_1.dcl\n"
        "TEXTURE_TERRAIN 180 180 ../../common_textures/ground/lawn_collage_TRN.png\n"
        "TILE_LOD  20000\n"],

    ['sub_gdn_vdry',
        "DECAL_LIB   lib/g10/decals/AGS_suburban_garden_vdry_1.dcl\n"
        "TEXTURE_TERRAIN 220 220 ../../common_textures/ground/grass_vdry_patchy_TRN.png\n"
        "TILE_LOD  20000\n"],


    ['AGS_trailer_park_1',
        "DECAL_LIB   lib/g10/decals/AGS_shrub_dirt_green_key_1.dcl\n"],

    ['AGS_suburban_garden_dry_1',
        "DECAL_LIB   lib/g10/decals/AGS_suburban_garden_vdry_1.dcl\n"
        "TEXTURE_TERRAIN 200 200 ../../common_textures/ground/grass_dry_patchy_TRN.png\n"
        "TILE_LOD  20000\n"],

    ['AGS_suburban_garden_vdry_1',
        "DECAL_LIB   lib/g10/decals/AGS_suburban_garden_vdry_1.dcl\n"
        "TEXTURE_TERRAIN 220 220 ../../common_textures/ground/grass_vdry_patchy_TRN.png\n"
        "TILE_LOD  20000\n"],


    ['AGB_grass_and_asphalt_1',
        "DECAL_LIB   lib/g10/decals/AGB_grass_and_asphalt_1.dcl\n"
        "TEXTURE_TERRAIN 180 180 ../../common_textures/ground/grass_wet_patchy_TRN.png\n"],

    ['asphalt_gravel_edge',
        "DECAL_LIB	lib/g10/decals/asphalt_gravel_edge.dcl\n"],

    ['test2',
        "TEXTURE foo\n"
        "NORMAL bar\n"],

    ['test_tinting',
        "GLOBAL_tint  0.2  1.0\n"],

    ['cars_10',
        "#left is LFT(0), right is RGT(0)\n"
        "CAR_(DRP)	1  CTR(-4.932)  25  0.060000 1\n"
        "CAR_(DRP)	1  CTR(-1.692)  28  0.060000 1\n"
        "CAR_(DRP)	0  CTR(1.688)  28  0.060000 1\n"
        "CAR_(DRP)	0  CTR(4.938)  25  0.060000 1\n"],

    ['cars_hwy6',
        "#left is LFT(0), right is RGT(0)\n"
        "CAR_GRADED	0  CTR(-3.5) 30  0.019 0\n"
        "CAR_GRADED	0  CTR(0.0)  26  0.021 0\n"
        "CAR_GRADED	0  CTR(3.5)  22  0.023 1\n"
        "CAR_GRADED	0  CTR(6.5)  50  0.0015 2\n"],

    ['cars_hwy4',
        "#left is LFT(0), right is RGT(0)\n"
        "CAR_GRADED	0  CTR(0.0) 26  0.019 0\n"
        "CAR_GRADED	0  CTR(3.5)  22  0.021 1\n"
        "CAR_GRADED	0  CTR(6.0)  60  0.0012 2\n"],

    ['cars_ramp',
        "#left is LFT(0), right is RGT(0)\n"
        "CAR_(DRP)	0  CTR(0.0)  21  0.010 1\n"
        "CAR_(DRP)	0  CTR(3.0)  50  0.001 2\n"],

    ['cars_primary',
        "#left is LFT(0), right is RGT(0)\n"
        "CAR_(DRP)	1  CTR(-4.9375)  22 0.020 1 \n"
        "CAR_(DRP)	1  CTR(-1.6875) 27  0.018 0 \n"
        "CAR_(DRP)	0  CTR(1.6875) 27  0.018 0 \n"
        "CAR_(DRP)	0  CTR(4.9375)  17  0.0200 1 \n"],

    ['cars_primary_WW',
        "#left is LFT(0), right is RGT(0)\n"
        "CAR_(DRP)	1  CTR(-4.9375)  16  0.055000 1 \n"
        "CAR_(DRP)	1  CTR(-1.6875) 10  0.04 0 \n"
        "CAR_(DRP)	0  CTR(1.6875) 13  0.0580 \n"
        "CAR_(DRP)	0  CTR(4.9375)  12  0.06 1 \n"],

    ['cars_primary_oneway',
        "#left is LFT(0), right is RGT(0)\n"
        "CAR_(DRP)	0  CTR(0)     27  0.017 0 \n"
        "CAR_(DRP)	0  CTR(3.25)  24  0.0200 1 \n"],
    ['cars_primary_oneway_WW',
        "#left is LFT(0), right is RGT(0)\n"
        "CAR_(DRP)	0  CTR(0)     13  0.055 0 \n"
        "CAR_(DRP)	0  CTR(3.25)  12  0.06 1 \n"],

    ['cars_secondary',
        "#left is LFT(0), right is RGT(0)\n"
        "CAR_(DRP)	1  CTR(-1.6875)  22  0.0160 1 \n"
        "CAR_(DRP)	0  CTR(1.6875)  24  0.018 1 \n"],

    ['cars_secondary_oneway',
        "#left is LFT(0), right is RGT(0)\n"
        "CAR_(DRP)	0  CTR(-1.8)  22  0.017000 0 \n"
        "CAR_(DRP)	0  CTR(1.8)  20  0.0180 1 \n"],

    ['cars_secondary_WW',
        "#left is LFT(0), right is RGT(0)\n"
        "CAR_(DRP)	1  CTR(-1.6875)  14  0.0500 1 \n"
        "CAR_(DRP)	0  CTR(1.6875)  12  0.0500 1 \n"],

    ['cars_secondary_oneway_WW',
        "#left is LFT(0), right is RGT(0)\n"
        "CAR_(DRP)	0  CTR(-1.8)  13  0.05000 0 \n"
        "CAR_(DRP)	0  CTR(1.8)  10  0.050 1 \n"],

    ['cars_local',
        "#left is LFT(0), right is RGT(0)\n"
        "CAR_(DRP)	1  CTR(-1.6875)  17 0.01700 0 \n"
        "CAR_(DRP)	0  CTR(1.6875)  15 0.01700 0 \n"],

    ['cars_local_oneway',
        "#left is LFT(0), right is RGT(0)\n"
        "CAR_(DRP)	0  CTR(0)  17  0.01700 0 \n"],

    ['cars_local_WW',
        "#left is LFT(0), right is RGT(0)\n"
        "CAR_(DRP)	1  CTR(-1.6875)  12  0.045 1 \n"
        "CAR_(DRP)	0  CTR(1.6875)  10 0.045 1 \n"],

    ['cars_local_oneway_WW',
        "#left is LFT(0), right is RGT(0)\n"
        "CAR_(DRP)	0  CTR(0)  10 0.045 1 \n"],

    ['trains_primary',
        "CAR_(DRP)	0  CTR(0)  30	0.0025 3 \n"],

    ['trains_secondary',
        "CAR_(DRP)	0  CTR(0)  15  0.0021 4 \n"],

    ['trains_tertiary',
        "CAR_(DRP)	0  CTR(0)  7  0.000  5 \n"],

    ['trains_static',
        "OBJECT_(DRP)	DIST	lib/trains/F_13.33_gondola_empty.obj		CTR(0)	CTR(0)		0.0	0.0	13.33	13.33	200	800			5	5	\n"
        "OBJECT_FREQ     0.3 0.37	4096.0   0.3	1024.0  0.6		256.0	0.1		0.0	0.0  \n"
        "OBJECT_ALT	lib/trains/F_13.33_gondola.obj \n"
        "OBJECT_ALT	lib/trains/blank.obj \n"
        "OBJECT_ALT	lib/trains/blank.obj \n"
        "OBJECT_ALT	lib/trains/blank.obj \n"
        "OBJECT_ALT	lib/trains/blank.obj \n"
        "OBJECT_ALT	lib/trains/F_13.33_flatcar_empty.obj \n"
        "OBJECT_ALT	lib/trains/blank.obj \n"
        "OBJECT_ALT	lib/trains/blank.obj \n"
        "OBJECT_ALT	lib/trains/blank.obj \n"
        "OBJECT_ALT	lib/trains/blank.obj \n"
        "OBJECT_ALT	lib/trains/F_13.33_tanker.obj \n"
        "OBJECT_ALT	lib/trains/blank.obj \n"
        "OBJECT_ALT	lib/trains/blank.obj \n"
        "OBJECT_ALT	lib/trains/blank.obj \n"
        "OBJECT_ALT	lib/trains/blank.obj \n"
        "OBJECT_ALT	lib/trains/F_13.33_hopper.obj\n"
        "OBJECT_ALT	lib/trains/blank.obj \n"
        "OBJECT_ALT	lib/trains/blank.obj \n"
        "OBJECT_ALT	lib/trains/blank.obj \n"
        "OBJECT_ALT	lib/trains/blank.obj \n"

        "OBJECT_(DRP)	DIST	lib/trains/F_17.33_flatcar_long_empty.obj	CTR(0)	CTR(0)		0.0	0.0	17.33	17.43	250	500         4	4	\n"
        "OBJECT_FREQ     0.2  0.3		4096.0   0.3	1024.0  0.6		256.0	0.1		0.0	0.0  \n"
        "OBJECT_ALT	lib/trains/blank.obj \n"
        "OBJECT_ALT	lib/trains/blank.obj \n"
        "OBJECT_ALT	lib/trains/blank.obj \n"
        "OBJECT_ALT	lib/trains/blank.obj \n"
        "OBJECT_ALT	lib/trains/blank.obj \n"
        "OBJECT_ALT	lib/trains/blank.obj \n"

        "OBJECT_(DRP)	DIST	lib/trains/HS_body.obj				CTR(0)	CTR(0)		0.0	0.0	27.6	27.7	300	1000			6	6    \n"
        "OBJECT_FREQ     0.73  0.84		4096.0   0.3	1024.0  0.6		256.0	0.1		0.0	0.0  \n"
        "OBJECT_ALT	lib/trains/blank.obj \n"
        "OBJECT_ALT	lib/trains/blank.obj \n"
        "OBJECT_ALT	lib/trains/blank.obj \n"],


    ['lights_barrier_hwy',
        "#left is LFT(0), right is RGT(0)\n"
        "OBJECT_GRADED	DIST	lib/g10/streetlights/HwyLt1BarMnt.obj	LFT(0.125) LFT(0.125)	90.0 90.0	96	96	0.2/47.7	0.2/47.7	2 2	\n"
        "OBJECT_FREQ     0.0  0.15	8192.0   0.5	2048.0  0.5	0.0	0.0	0.0	0.0  \n"
        "OBJECT_GRADED	DIST	lib/g10/streetlights/HwyLt1BarMnt.obj	RGT(-0.125) RGT(-0.125)	-90.0 -90.0	96	96	48.2/47.7	48.2/47.7	2 2 \n"
        "OBJECT_FREQ     0.0  0.15	8192.0   0.5	2048.0  0.5	0.0	0.0		0.0	0.0  \n"
        "OBJECT_GRADED	DIST	lib/g10/streetlights/HwyLt3BarMnt.obj	RGT(-0.125) RGT(-0.125)	-90.0 -90.0	48	48	0.2/24	0.2/24	2 2 \n"
        "OBJECT_FREQ     0.15  0.5	8192.0   0.5	2048.0  0.5	0.0	0.0	0.0	0.0  \n"

        "OBJECT_GRADED	DIST	lib/g10/streetlights/HwyLt2BarMnt.obj	LFT(0.125) LFT(0.125)	90.0 90.0	80	80	0.2/39.7	0.2/39.7	2 2 \n"
        "OBJECT_FREQ     0.5  0.65	8192.0   0.5	2048.0  0.5	0.0	0.0		0.0	0.0  \n"
        "OBJECT_GRADED	DIST	lib/g10/streetlights/HwyLt2BarMnt.obj	RGT(-0.125) RGT(-0.125)	-90.0 -90.0	80	80	40.2/39.7	40.2/39.7	2 2 \n"
        "OBJECT_FREQ     0.5  0.65	8192.0   0.5	2048.0  0.5	0.0	0.0		0.0	0.0  \n"
        "OBJECT_GRADED	DIST	lib/g10/streetlights/HwyLt2BarMnt.obj	RGT(-0.125) RGT(-0.125)	-90.0 -90.0	64	64	0.2/32	0.2/32	2 2 \n"
        "OBJECT_FREQ     0.65  1.0	8192.0   0.5	2048.0  0.5	0.0	0.0		0.0	0.0  \n"],

    ['lights_ground_hwy',
        "#left is LFT(0), right is RGT(0)\n"
        "OBJECT_(DRP)	DIST	lib/g10/streetlights/HwyLt1GndMnt.obj	LFT(0.25) LFT(0.25)	90.0 90.0	96	96	48/48	48/48	2 2 \n"
        "OBJECT_ALT	lib/g10/streetlights/HwyLt2GndMnt.obj \n"
        "OBJECT_(DRP)	DIST	lib/g10/streetlights/HwyLt1GndMnt.obj	RGT(-0.25) RGT(-0.25)	-90.0 -90.0	96	96	96/48	96/48	2 2 \n"
        "OBJECT_ALT	lib/g10/streetlights/HwyLt2GndMnt.obj \n"],

    ['lights_barrier_ramp',
        "#left is LFT(0), right is RGT(0)\n"
        "OBJECT_GRADED	DIST	lib/g10/streetlights/RmpLt1BarMnt.obj	RGT(-4.125) RGT(-4.125)	-90.0 -90.0	64	64	0.2/32	0.2/32	2 2 \n"
        "OBJECT_FREQ     0.0  0.5	8192.0   0.5	2048.0  0.5	0.0	0.0		0.0	0.0  \n"
        "OBJECT_GRADED	DIST	lib/g10/streetlights/RmpLt2BarMnt.obj	RGT(-4.125) RGT(-4.125)	-90.0 -90.0	56	56	16.2/32	16.2/32	2 2 \n"
        "OBJECT_FREQ     0.5  1.0	8192.0   0.5	2048.0  0.5	0.0	0.0		0.0	0.0  \n"],

    ['lights_ground_ramp',
        "#left is LFT(0), right is RGT(0)\n"
        "OBJECT_(DRP)	DIST	lib/g10/streetlights/RmpLt1GndMnt.obj	RGT(-3.5) RGT(-3.5)	-90.0 -90.0	63	66	10/32	16/32	2 2 \n"
        "OBJECT_FREQ     0.0  0.5	8192.0   0.5	2048.0  0.5	0.0	0.0		0.0	0.0  \n"
        "OBJECT_(DRP)	DIST	lib/g10/streetlights/RmpLt2GndMnt.obj	RGT(-3.5) RGT(-3.5)	-90.0 -90.0	55	57	10/32	16/32	2 2 \n"
        "OBJECT_FREQ     0.5  1.0	8192.0   0.5	2048.0  0.5	0.0	0.0		0.0	0.0  \n"],

    ['hwy_lt_freq_1',
        "OBJECT_FREQ     0.0  0.5	8192.0   0.5	2048.0  0.5	0.0	0.0	0.0	0.0  \n"],

    ['hwy_lt_freq_2',
        "OBJECT_FREQ     0.5  1.0	8192.0   0.5	2048.0  0.5	0.0	0.0	0.0	0.0  \n"],

    ['res_lt_freq_1',
        "OBJECT_FREQ     0.0  0.5	4096.0   0.5	1024.0  0.5	0.0	0.0	0.0	0.0  \n"],

    ['res_lt_freq_2',
        "OBJECT_FREQ     0.5  1.0	4096.0   0.5	1024.0  0.5	0.0	0.0	0.0	0.0  \n"],

    ['streetlights_local_rural',
        "#left is LFT(0), right is RGT(0)\n"
        "OBJECT_(DRP)	DIST	lib/g10/streetlights/ResLt1V1.obj		LFT(4) LFT(4)	90.0 90.0	120	140	14	20		2 2 \n"
        "OBJECT_FREQ     0 0.12		4096.0   0.5  2048.0   0.25  512  0.25   0.0   0.0 \n"
        "OBJECT_ALT	lib/g10/streetlights/ResShort.obj \n"
        "OBJECT_(DRP)	DIST	lib/g10/streetlights/ResLt1V1.obj		RGT(-4) RGT(-4)	-90.0 -90.0	120	140	50	70    2	2	\n"
        "OBJECT_FREQ     0.12 0.25	4096.0   0.5  2048.0   0.25  512 0.25   0.0   0.0 \n"
        "OBJECT_ALT	lib/g10/streetlights/ResShort.obj \n"

        "OBJECT_(DRP)	DIST	lib/g10/streetlights/ResLt1V2.obj		LFT(4) LFT(4)	90.0 90.0	160	180	15	20   2 2 \n"
        "OBJECT_FREQ     0.25  0.375	4096.0   0.5  2048.0   0.25 512  0.25   0.0   0.0  \n"
        "OBJECT_ALT	lib/g10/streetlights/ResLt2Dim.obj \n"
        "OBJECT_(DRP)	DIST	lib/g10/streetlights/ResLt1V2.obj		RGT(-4) RGT(-4)	-90.0 -90.0	160	180	15	20    2 2 \n"
        "OBJECT_FREQ     0.375  0.5	4096.0   0.5  2048.0   0.25 512  0.25    0.0   0.0  \n"
        "OBJECT_ALT	lib/g10/streetlights/ResLt2Dim.obj \n"


        "OBJECT_(DRP)	CREASE	lib/g10/streetlights/ResLt3.obj		LFT(4) LFT(4)	90.0 90.0	150	180	13	30		2 2 \n"
        "OBJECT_FREQ     0.5  0.625  4096.0   0.5  2048.0   0.25	512  0.25   0.0   0.0  \n"
        "OBJECT_ALT	lib/g10/streetlights/ResLt1V1.obj \n"
        "OBJECT_(DRP)	CREASE	lib/g10/streetlights/ResLt3.obj		RGT(-4) RGT(-4)	-90.0 -90.0	150	180	13	30		2 2 \n"
        "OBJECT_FREQ     0.625  0.75  4096.0   0.5  2048.0   0.25	512  0.25   0.0   0.0  \n"
        "OBJECT_ALT	lib/g10/streetlights/ResLt1V1.obj \n"],


    ['streetlights_res_LH_SW',
        "#left is LFT(0), right is RGT(0)\n"
        "OBJECT_(DRP)	DIST	lib/g10/streetlights/ResLt1V1.obj		LFT(4.0) LFT(4.1)	90.0 90.0	90	100	90/30	100/30		2 2     \n"
        "OBJECT_FREQ     0.0 0.5	4096.0   0.5	1024.0  0.5	0.0	0.0	0.0	0.0 \n"
        "OBJECT_ALT	lib/g10/streetlights/ResLt1V2.obj \n"
        "OBJECT_FREQ     0.0 0.5	4096.0   0.5	1024.0  0.5	0.0	0.0	0.0	0.0 \n"
        "OBJECT_(DRP)	DIST	lib/g10/streetlights/ResLt1V1.obj		LFT(4.0) LFT(4.1)	90.0 90.0	80	90	70/30	80/30		2 2	\n"
        "OBJECT_FREQ     0.5  1.0	4096.0   0.5	1024.0  0.5	0.0	0.0	0.0	0.0  \n"
        "OBJECT_ALT	lib/g10/streetlights/ResLt1V2.obj \n"
        "OBJECT_FREQ     0.5  1.0	4096.0   0.5	1024.0  0.5	0.0	0.0	0.0	0.0  \n"
        ],

    ['streetlights_res_RH_SW',
        "#left is LFT(0), right is RGT(0)\n"
        "OBJECT_(DRP)	DIST	lib/g10/streetlights/ResLt1V1.obj		RGT(-4.0) RGT(-4.1)	-90.0 -90.0	90	100	90/30	100/30		2 2	\n"
        "OBJECT_FREQ     0.0 0.5	4096.0   0.5	1024.0  0.5	0.0	0.0	0.0	0.0   \n"
        "OBJECT_ALT	lib/g10/streetlights/ResLt3.obj \n"
        "OBJECT_(DRP)	DIST	lib/g10/streetlights/ResLt1V2.obj		RGT(-4.0) RGT(-4.1)	-90.0 -90.0	80	90	80/30	90/30		2 2     \n"
        "OBJECT_FREQ     0.5  1.0	4096.0   0.5	1024.0  0.5	0.0	0.0	0.0	0.0  \n"
        "OBJECT_ALT	lib/g10/streetlights/ResLt2Dim.obj \n"
        ],

    ['streetlights_res_both_SW',
        "#left is LFT(0), right is RGT(0)\n"
        "OBJECT_(DRP)	DIST	lib/g10/streetlights/ResLt1V1.obj		LFT(4.0) LFT(4.0)	90.0 90.0	150	160	70/70	85/85		2 2	\n"
        "OBJECT_FREQ	0.0 0.5		4096.0   0.5	1024.0  0.5	0.0	0.0	0.0	0.0   \n"
        #"OBJECT_ALT	lib/g10/streetlights/ResLt1V2.obj \n"
        "OBJECT_(DRP)	DIST	lib/g10/streetlights/ResLt1V1.obj		RGT(-4.0) RGT(-4.0)	-90.0 -90.0	150	160	150/70	160/70		2 2 \n"
        "OBJECT_FREQ	0.0 0.5		4096.0   0.5	1024.0  0.5	0.0	0.0	0.0	0.0   \n"
        #"OBJECT_ALT	lib/g10/streetlights/ResLt1V2.obj \n"
        "OBJECT_(DRP)	DIST	lib/g10/streetlights/ResLt1V2.obj		LFT(4.0) LFT(4.0)	90.0 90.0	130	140	60/60	70/70		2 2 \n"
        "OBJECT_FREQ     0.5  1.0	4096.0   0.5	1024.0  0.5	0.0	0.0	0.0	0.0 \n"
        "OBJECT_ALT	lib/g10/streetlights/ResLt2.obj \n"
        "OBJECT_(DRP)	DIST	lib/g10/streetlights/ResLt1V2.obj		RGT(-4.0) RGT(-4.0)	-90.0 -90.0	130	140	130/60	140/70		2 2 \n"
        "OBJECT_FREQ     0.5  1.0	4096.0   0.5	1024.0  0.5	0.0	0.0	0.0	0.0  \n"
        "OBJECT_ALT	lib/g10/streetlights/ResLt2.obj \n"
        ],
    ['streetlights_res_both_WW',
        "#left is LFT(0), right is RGT(0)\n"
        "OBJECT_(DRP)	DIST	lib/g10/streetlights/ResLt1V1.obj		LFT(4.0) LFT(4.0)	90.0 90.0	120	130	60/60	65/65		2 2 \n"
        "OBJECT_FREQ	0.0 0.5		4096.0   0.5	1024.0  0.5	0.0	0.0	0.0	0.0     \n"
        "OBJECT_(DRP)	DIST	lib/g10/streetlights/ResLt1V1.obj		RGT(-4.0) RGT(-4.0)	-90.0 -90.0	120	130	120/60	130/65		2 2 \n"
        "OBJECT_FREQ     0.0 0.5	4096.0   0.5	1024.0  0.5	0.0	0.0	0.0	0.0    \n"
        "OBJECT_(DRP)	DIST	lib/g10/streetlights/ResLt1V2.obj		LFT(4.0) LFT(4.0)	90.0 90.0	90	100	45/45	50/50		2 2 \n"
        "OBJECT_FREQ     0.5  1.0	4096.0   0.5	1024.0  0.5	0.0	0.0	0.0	0.0  \n"
        "OBJECT_ALT	lib/g10/streetlights/ResLt2.obj \n"
        "OBJECT_FREQ     0.5  1.0	4096.0   0.5	1024.0  0.5	0.0	0.0	0.0	0.0  \n"
        "OBJECT_(DRP)	DIST	lib/g10/streetlights/ResLt1V2.obj		RGT(-4.0) RGT(-4.0)	-90.0 -90.0	90	100	90/45	100/50      2 2 \n"
        "OBJECT_FREQ     0.5  1.0	4096.0   0.5	1024.0  0.5	0.0	0.0	0.0	0.0 \n"
        "OBJECT_ALT	lib/g10/streetlights/ResLt2.obj \n"
        "OBJECT_FREQ     0.5  1.0	4096.0   0.5	1024.0  0.5	0.0	0.0	0.0	0.0 \n"
        ],
    ['streetlights_secondary_both_WW',
        "#left is LFT(0), right is RGT(0)\n"
        "OBJECT_(DRP)	DIST	lib/g10/streetlights/ResLt1V1.obj		LFT(4.0) LFT(4.0)	90.0 90.0	80	90	40	45		2 2		\n"
        "OBJECT_FREQ	0.0 0.5		4096.0   0.5	1024.0  0.5	0.0	0.0	0.0	0.0     \n"
        "OBJECT_(DRP)	DIST	lib/g10/streetlights/ResLt1V2.obj		LFT(4.0) LFT(4.0)	90.0 90.0	100	110	50	55		2 2 \n"
        "OBJECT_FREQ	0.5 1.0		4096.0   0.5	1024.0  0.5	0.0	0.0	0.0	0.0     \n"

        "OBJECT_(DRP)	DIST	lib/g10/streetlights/ResLt1V1.obj		RGT(-4.0) RGT(-4.0)	-90.0 -90.0	80	90	80/40	90/45		2 2 \n"
        "OBJECT_FREQ	0.0 0.5		4096.0   0.5	1024.0  0.5	0.0	0.0	0.0	0.0     \n"
        "OBJECT_(DRP)	DIST	lib/g10/streetlights/ResLt1V2.obj		RGT(-4.0) RGT(-4.0)	-90.0 -90.0	100	110	100/50	110/55		2 2 \n"
        "OBJECT_FREQ	0.5  1.0	4096.0   0.5	1024.0  0.5	0.0	0.0	0.0	0.0     \n"

        #"OBJECT_(DRP)	DIST	lib/g10/streetlights/ResLt1V2.obj		LFT(4.0) LFT(4.0)	90.0 90.0	90	100	45	50			2 2 \n"
        #"OBJECT_FREQ    0.5  1.0 2048.0   0.0 512.0   1.0   128.0  0.0    32.0   0.0 \n"
        #"OBJECT_ALT	lib/g10/streetlights/ResLt1V2.obj \n"
        #"OBJECT_(DRP)	DIST	lib/g10/streetlights/ResLt1V2.obj		RGT(-4.0) RGT(-4.0)	-90.0 -90.0	90	100	90/45	100/50			2 2 \n"
        #"OBJECT_FREQ    0.5  1.0 2048.0   0.0  512.0   1.0  128.0  0.0    32.0   0.0 \n"
        #"OBJECT_ALT	lib/g10/streetlights/ResLt1V2.obj \n"
        ],

    ['streetlights_primary_WW',
        "#left is LFT(0), right is RGT(0)\n"
        "OBJECT_(DRP)	DIST	lib/g10/streetlights/PrimaryLt1.obj		LFT(4.0) LFT(4.0)	90.0 90.0	64	70	32/32	34/34		2 2 \n"
        "OBJECT_FREQ	0.0 0.5		4096.0   0.5	1024.0  0.5	0.0	0.0	0.0	0.0   \n"
        "OBJECT_(DRP)	DIST	lib/g10/streetlights/PrimaryLt1.obj		RGT(-4.0) RGT(-4.0)	-90.0 -90.0	64	70	63/32	70/35		2 2 \n"
        "OBJECT_FREQ	0.0 0.5		4096.0   0.5	1024.0  0.5	0.0	0.0	0.0	0.0   \n"

        "OBJECT_(DRP)	DIST	lib/g10/streetlights/ResLt3.obj			LFT(4.0) LFT(4.0)	90.0 90.0	62	65	31/31	33/33		2 2 \n"
        "OBJECT_FREQ     0.5  1.0	4096.0   0.5	1024.0  0.5	0.0	0.0	0.0	0.0 \n"
        "OBJECT_(DRP)	DIST	lib/g10/streetlights/ResLt3.obj			RGT(-4.0) RGT(-4.0)	-90.0 -90.0	62	65	62/31	65/33		2 2 \n"
        "OBJECT_FREQ     0.5  1.0	4096.0   0.5	1024.0  0.5	0.0	0.0	0.0	0.0 \n"],

    ['streetlights_primary_oneway_WW',
        "#left is LFT(0), right is RGT(0)\n"

        "OBJECT_(DRP)	DIST	lib/g10/streetlights/PrimaryLt1.obj		RGT(-4.0) RGT(-4.0)	-90.0 -90.0	40	48	30	34		2 2 \n"
        "OBJECT_FREQ	0.0 0.5		4096.0   0.5	1024.0  0.5	0.0	0.0	0.0	0.0   \n"
        "OBJECT_(DRP)	DIST	lib/g10/streetlights/ResLt3.obj			RGT(-4.0) RGT(-4.0)	-90.0 -90.0	36	42	36	42		2 2 \n"
        "OBJECT_FREQ     0.5  1.0	4096.0   0.5	1024.0  0.5	0.0	0.0	0.0	0.0 \n"],

    ['caps_hwy6',

        "OBJECT_GRADED	BEGIN	lib/roads/EndHwyCncLH.obj	LFT(0) LFT(0)		0.0 0.0		0.0 0.0		0.0 0.0	\n"
        "OBJECT_GRADED	BEGIN	lib/roads/EndHwyCncRH.obj	RGT(0) RGT(0)		0.0 0.0		0.0 0.0		0.0 0.0	\n"
        "OBJECT_GRADED	END	lib/roads/EndHwyCncRH.obj	LFT(0) LFT(0)		-180.0 -180.0	0.0 0.0		0.0 0.0	\n"
        "OBJECT_GRADED	END	lib/roads/EndHwyCncLH.obj	RGT(0) RGT(0)		-180.0 -180.0	0.0 0.0		0.0 0.0	\n"],

    ['caps_secondary_bridge',

        "OBJECT_GRADED	BEGIN	objects/structures/CapLocBrkV0.obj	LFT(2.5) LFT(2.5)		0.0 0.0			0.0 0.0		0.0 0.0		2 2 \n"
        "OBJECT_ALT				objects/structures/CapLocBrkV1.obj \n"
        "OBJECT_ALT				objects/structures/CapLocBrkV2.obj \n"
        "OBJECT_ALT				objects/structures/CapLocBrkV3.obj \n"
        "OBJECT_GRADED	BEGIN	objects/structures/CapLocBrkV0.obj	RGT(-2.5) RGT(-2.5)		-180.0 -180.0	0.0 0.0		0.0 0.0		2 2 \n"
        "OBJECT_ALT				objects/structures/CapLocBrkV1.obj \n"
        "OBJECT_ALT				objects/structures/CapLocBrkV2.obj \n"
        "OBJECT_ALT				objects/structures/CapLocBrkV3.obj \n"
        "OBJECT_GRADED	END		objects/structures/CapLocBrkV0.obj	LFT(2.5) LFT(2.5)		0.0 0.0			0.0 0.0		0.0 0.0		2 2 \n"
        "OBJECT_ALT				objects/structures/CapLocBrkV1.obj \n"
        "OBJECT_ALT				objects/structures/CapLocBrkV2.obj \n"
        "OBJECT_ALT				objects/structures/CapLocBrkV3.obj \n"
        "OBJECT_GRADED	END		objects/structures/CapLocBrkV0.obj	RGT(-2.5) RGT(-2.5)		-180.0 -180.0	0.0 0.0		0.0 0.0		2 2 \n"
        "OBJECT_ALT				objects/structures/CapLocBrkV1.obj \n"
        "OBJECT_ALT				objects/structures/CapLocBrkV2.obj \n"
        "OBJECT_ALT				objects/structures/CapLocBrkV3.obj \n"],

    ['sign_bridges_barrier_hwy6',
        "#left is LFT(0), right is RGT(0)\n"
        "OBJECT_GRADED	DIST	lib/g10/roadsigns/SignBridge6LaneUrban.obj	CTR(0.375) CTR(0.375)	0.0 0.0  100	500	100	200			4	6 \n"
        "OBJECT_FREQ     0.0  0.49999     1000.0   0.0  250.0   0.0   75.0   0.0   20.0   1.0 \n"
        "OBJECT_GRADED	DIST	lib/g10/roadsigns/misc_shoulder.obj	RGT(-0.125) RGT(-0.125)        0.0 0.0   100	500	100	200			4	6 \n"
        "OBJECT_FREQ     0.5   1.00   1000.0   0.0  250.0   0.0    75.0   0.0   20.0   1.0 \n"],

    ['parked_cars_sparse',
        "#left is LFT(0), right is RGT(0)\n"
        "OBJECT_(DRP)	DIST	lib/cars/car_static.obj		LFT(5.4) LFT(5.625)	177 183  6	8	20	30		4	6 \n"
        "OBJECT_FREQ     0.4  0.55  128.0   0.10  64.0   0.20    32.0   0.2   8.0   0.5 \n"
        "OBJECT_(DRP)	DIST	lib/cars/car_static.obj	RGT(-5.4) RGT(-5.625)	-2 2     6	8	20	30		4	6   \n"
        "OBJECT_FREQ     0.45  0.6  128.0   0.10  64.0   0.20    32.0   0.2   8.0   0.5  \n"],
    ['parked_cars_sparse_oneway',
        "#left is LFT(0), right is RGT(0)\n"
        "OBJECT_(DRP)	DIST	lib/cars/car_static.obj		LFT(5.4) LFT(5.625)	-3 3     6	8	20	30		4	6   \n"
        "OBJECT_FREQ     0.45 0.5	128.0   0.10  64.0   0.20    32.0   0.2   8.0   0.5 \n"
        "OBJECT_(DRP)	DIST	lib/cars/car_static.obj		RGT(-5.4) RGT(-5.625)	-3 3     6	8	20	30		4	6   \n"
        "OBJECT_FREQ      0.5  0.55	128.0   0.10  64.0   0.20    32.0   0.2   8.0   0.5 \n"],
    ['parked_cars_dense',
        "#left is LFT(0), right is RGT(0)\n"
        "OBJECT_(DRP)	DIST	lib/cars/car_static.obj		LFT(5.4) LFT(5.625)	177 183  6	7	20	25			4	6 \n"
        "OBJECT_FREQ     0.3  0.5	128.0   0.10  64.0   0.20    32.0   0.2   8.0   0.5  \n"
        "OBJECT_(DRP)	DIST	lib/cars/car_static.obj		LFT(5.4) LFT(5.625)	-3 3     6	7	20	25			4	6 \n"
        "OBJECT_FREQ     0.5 0.55	128.0   0.10  64.0   0.20    32.0   0.2   8.0   0.5  \n"
        "OBJECT_(DRP)	DIST	lib/cars/car_static.obj		RGT(-5.4) RGT(-5.625)	-3 3     6	7	20	25			4	6 \n"
        "OBJECT_FREQ     0.5 0.7	128.0   0.10  64.0   0.20    32.0   0.2   8.0   0.5  \n"
        "OBJECT_(DRP)	DIST	lib/cars/car_static.obj		RGT(-5.4) RGT(-5.625)	177 183  6	7	20	25			4	6 \n"
        "OBJECT_FREQ     0.7 0.8	128.0   0.10  64.0   0.20    32.0   0.2   8.0   0.5  \n"],

    ['parked_cars_dense_oneway',
        "#left is LFT(0), right is RGT(0)\n"
        "OBJECT_(DRP)	DIST	lib/cars/car_static.obj		LFT(5.4) LFT(5.625)	-3 3     6	7	18	25			4	6 \n"
        "OBJECT_FREQ     0.3  0.6	128.0   0.10  64.0   0.20    32.0   0.2   8.0   0.5\n"
        "OBJECT_(DRP)	DIST	lib/cars/car_static.obj		RGT(-5.4) RGT(-5.625)	-3 3     6	7	18	25			4	6 \n"
        "OBJECT_FREQ      0.5 0.7	128.0   0.10  64.0   0.20    32.0   0.2   8.0   0.5 \n"],


    ['rail_signals_primary_draped',
        "#left is LFT(0), right is RGT(0)\n"
        "OBJECT_(DRP)	DIST	lib/g10/railroads/signal_CL_high.obj	RGT(-5) RGT(-5)	0.0 0.0		1600  1600      500 1600        4	6 \n"
        "OBJECT_FREQ	0.0 0.5			4096.0   0.5	512.0  0.15	128.0	0.15	32.0	0.2   \n"
        "OBJECT_(DRP)	DIST	lib/g10/railroads/signal_CPL_high.obj	RGT(-5) RGT(-5)	0.0 0.0		1600  1600      500 1600        4	6 \n"
        "OBJECT_FREQ     0.5  1.0		4096.0   0.5	512.0  0.15	128.0	0.15	32.0	0.2 \n"],

    ['rail_signals_primary_embanked',
        "#left is LFT(0), right is RGT(0)\n"
        "OBJECT_GRADED	DIST	lib/g10/railroads/signal_CL_embanked.obj	RGT(-5) RGT(-5)	0.0 0.0		1600    1600        500 1600        4	6 \n"
        "OBJECT_FREQ	0.0 0.5			4096.0   0.5	512.0  0.15	128.0	0.15	32.0	0.2  \n"
        "OBJECT_GRADED	DIST	lib/g10/railroads/signal_CPL_high.obj	RGT(-5) RGT(-5)	0.0 0.0		1600  1600      500 1600        4	6 \n"
        "OBJECT_FREQ     0.5  1.0		4096.0   0.5	512.0  0.15	128.0	0.15	32.0	0.2 \n"],

    ['rail_signals_secondary_draped',
        "#left is LFT(0), right is RGT(0)\n"
        "OBJECT_(DRP)	DIST	lib/g10/railroads/signal_CL_high.obj	RGT(-5) RGT(-5)	0.0 0.0		1600 1600		500 1600        4	6 \n"
        "OBJECT_FREQ	0.0 0.5		4096.0   0.5	512.0  0.15	128.0	0.15	32.0	0.2   \n"
        "OBJECT_(DRP)	DIST	lib/g10/railroads/signal_CPL_high.obj	RGT(-5) RGT(-5)	0.0 0.0		1600 1600		500 1600        4	6 \n"
        "OBJECT_FREQ	0.5 1.0		4096.0   0.5	512.0  0.15	128.0	0.15	32.0	0.2  \n"],

    ['rail_clutter_secondary',
        "#left is LFT(0), right is RGT(0)\n"
        "OBJECT_(DRP)	DIST	objects/misc/LooseRailsV1.obj	CTR(2.5) CTR(3.0)	1.0 3.0		19.5    20.5		400 2000        5	6 \n"
        "OBJECT_FREQ	0.70 0.8		1024.0   0.5	256.0  0.5	0.0	0.0	0.0	0.0   \n"],

    ['rail_clutter_tertiary',
        "#left is LFT(0), right is RGT(0)\n"
        "OBJECT_(DRP)	DIST	objects/misc/TrunkingV1.obj	CTR(2.0) CTR(2.0)	0.0 0.0		16.0    16.0		200 1000        5	6 \n"
        "OBJECT_FREQ	0.45 0.55		1024.0   0.5	256.0  0.55	0.0	0.0	0.0	0.0   \n"
        "OBJECT_ALT	objects/misc/TrunkingV2.obj\n"
        "OBJECT_ALT	objects/misc/TrunkingV3.obj\n"
        "OBJECT_ALT	objects/misc/TrunkingV4.obj\n"
        "OBJECT_ALT	objects/misc/TrunkingV5.obj\n"
        "OBJECT_ALT	objects/misc/TrunkingV6.obj\n"
        "OBJECT_ALT	objects/misc/TrunkingV7.obj\n"],


    ['rail_veg_primary',
        "#left is LFT(0), right is RGT(0)\n"
        "OBJECT_DRAPED	DIST	lib/g10/forests/autogen_tree_any.obj	RGT(-0.25) RGT(2.0)	-180.0 180.0		5	25		300 500		4	6 \n"
        "OBJECT_FREQ	0.5 0.8		2048.0   0.25	512.0  0.25		128.0	0.5	0.0	0.0   \n"],

    ['hwy_veg',
        "OBJECT_DRAPED	DIST	lib/g10/forests/autogen_tree1.obj	RGT(5) RGT(10)	-90.0 90.0		3	20		100 500         4	6\n"
        "OBJECT_FREQ	0.2 0.5		2048   0.25	512.0  0.15		256.0	0.2	32.0	0.4 \n"
        "OBJECT_DRAPED	DIST	lib/g10/forests/autogen_tree2.obj	RGT(3) RGT(10)	-90.0 90.0		5	19		150 550         4	6\n"
        "OBJECT_FREQ	0.4 0.7		2048   0.25	512.0  0.15		256.0	0.2	32.0	0.4 \n"
        "OBJECT_DRAPED	DIST	lib/g10/forests/autogen_tree2.obj	RGT(3) RGT(10)	-90.0 90.0		6	22		200 650         4	6\n"
        "OBJECT_FREQ	0.6 0.9		2048   0.25	512.0  0.15		256.0	0.2	32.0	0.4 \n"
        "OBJECT_DRAPED	DIST	lib/g10/forests/autogen_tree2.obj	RGT(3) RGT(10)	-90.0 90.0		5	24		250 700         4	6\n"
        "OBJECT_FREQ	0.8 1.0		2048   0.25	512.0  0.15		256.0	0.2	32.0	0.4 \n"],

    ['trees_primary',
        "#left is LFT(0), right is RGT(0)\n"
        "OBJECT_DRAPED	DIST	lib/g10/forests/autogen_tree2.obj	RGT(-1) RGT(1)	-90.0 90.0		7	20		30 70       4	6 \n"
        "OBJECT_FREQ	0.125 0.625		1000.0   0.5	250.0  0.25		64.0	0.15	16.0	0.1 \n"
        "OBJECT_ALT		objects/blank.obj \n"
        "OBJECT_DRAPED	DIST	lib/g10/forests/autogen_tree4.obj	RGT(-1) RGT(1.5)	-90.0 90.0		5	17		40 90       4	6 \n"
        "OBJECT_FREQ	0.375 0.75		1000.0   0.5	250.0  0.25		64.0	0.15	16.0	0.1 \n"
        "OBJECT_ALT		objects/blank.obj \n"
        "OBJECT_DRAPED	DIST	lib/g10/forests/autogen_tree2.obj	LFT(-1) LFT(1)		-90.0 90.0		7	20		30 70       4	6 \n"
        "OBJECT_FREQ	0.125 0.625		1000.0   0.5	250.0  0.25		64.0	0.15	16.0	0.1 \n"
        "OBJECT_ALT		objects/blank.obj \n"
        "OBJECT_DRAPED	DIST	lib/g10/forests/autogen_tree4.obj	LFT(-1.5) LFT(1)	-90.0 90.0		5	17		40 90       4	6 \n"
        "OBJECT_FREQ	0.375 0.75		1000.0   0.5	250.0  0.25		64.0	0.15	16.0	0.1 \n"
        "OBJECT_ALT		objects/blank.obj \n"]
    ]



def get_macro(name):
    for m in macros:
        if m[0].upper() == name.upper():
            return m[1]
    return None

def get_road_match(name):
    for m in road_matches:
        if m[0].upper() == name.upper():
            return m[1]
    return None

'''
Script to convert a FLEXPART dataset into a NetCDF4 file.

:Author: Francesc Alted
:Contact:  francesc@blosc.org
:Created:  2014-11-14
:Acknowledgment: Funding for the development of this code is provided
     through the iiSPAC project (NSF-ARC-1023651)

'''

from __future__ import print_function

import sys
import warnings
import platform
import getpass
import datetime
import os.path
import netCDF4 as nc


from reflexible.conv2netcdf4 import Header, read_grid, read_command

units = ['conc', 'pptv', 'time', 'footprint', 'footprint_total']


def output_units(ncid):
    if ncid.ldirect == 1:
        # forward simulation
        if ncid.ind_source == 1:
            if ncid.ind_receptor == 1:
                units = 'ng m-3'
            else:
                units = 'ng kg-1'
        else:
            if ncid.ind_receptor == 1:
                units = 'ng m-3'
            else:
                units = 'ng kg-1'
    else:
        # backward simulation
        if ncid.ind_source == 1:
            if ncid.ind_receptor == 1:
                units = 's'
            else:
                units = 's m3 kg-1'
        else:
            if ncid.ind_receptor == 1:
                units = 's kg m-3'
            else:
                units = 's'

    return units

def write_metadata(H, command, ncid):
    # hes CF convention requires these attributes
    ncid.Conventions = 'CF-1.6'
    ncid.title = 'FLEXPART model output'
    ncid.institution = 'NILU'
    ncid.source = H.version + ' model output'
    date = "%d-%d-%d %d:%d" % datetime.datetime.now().timetuple()[:5]
    zone = "NA"
    ncid.history = date + ' ' + zone + ' created by ' + getpass.getuser() + ' on ' + platform.node()
    ncid.references = 'Stohl et al., Atmos. Chem. Phys., 2005, doi:10.5194/acp-5-2461-200'

    # attributes describing model run
    ncid.outlon0 = H.outlon0
    ncid.outlat0 = H.outlat0
    ncid.dxout = H.dxout
    ncid.dyout = H.dyout

    # COMMAND file settings
    ncid.ldirect = 1 if H.direction == "forward" else -1
    ncid.ibdate = H.available_dates[0][:8]
    ncid.ibtime = H.available_dates[0][8:]
    ncid.iedate = H.available_dates[-1][:8]
    ncid.ietime = H.available_dates[-1][8:]
    ncid.loutstep = H.loutstep
    ncid.loutaver = H.loutaver
    ncid.loutsample = H.loutsample
    ncid.lsubgrid = H.lsubgrid
    ncid.lconvection = H.lconvection
    ncid.ind_source = H.ind_source
    ncid.ind_receptor = H.ind_receptor

    # COMMAND settings
    if len(command) > 0:
        ncid.itsplit = command['T_PARTSPLIT']
        ncid.linit_cond = command['LINIT_COND']
        ncid.lsynctime = command['SYNC']
        ncid.ctl = command['CTL']
        ncid.ifine = command['IFINE']
        ncid.iout = command['IOUT']
        ncid.ipout = command['IPOUT']
        ncid.lagespectra = command['LAGESPECTRA']
        ncid.ipin = command['IPIN']
        ncid.ioutputforeachrelease = command['OUTPUTFOREACHRELEASE']
        ncid.iflux = command['IFLUX']
        ncid.mdomainfill = command['MDOMAINFILL']
        ncid.mquasilag = command['MQUASILAG']
        ncid.nested_output = command['NESTED_OUTPUT']
        # This is a new option in V9.2
        ncid.surf_only = command.get('SURF_ONLY', 0)


def write_header(H, command, ncid):
    global units

    if len(command) > 0:
        iout = command['IOUT']
    else:
        # If COMMAND file not available, guess the value of IOUT
        unit_i = units.index(H.unit)
        iout = (unit_i) + (H.nested * 5)

    nnx = H.numxgrid
    nny = H.numygrid
    nnz = H.numzgrid
    # Parameter for data compression
    complevel = 9
    # Maximum number of chemical species per release (Source: par_mod.f90)
    # maxspec = 4
    # Variables defining the release locations, released species and their
    # properties, etc. (Source: com_mod.f90)
    species = H.species
    # decay = []
    # weightmolar = []
    # ohreact = []
    # kao = []
    # vsetaver = []
    # spec_ass = []
    # weta = []
    # wetb = []
    # weta_in = []
    # wetb_in = []
    # wetc_in = []
    # wetd_in = []
    # dquer = []
    # henry = []
    # dryvel = []
    # reldiff = []
    # f0 = []
    # density = []
    # dsigma = []
    lage = H.lage
    # Source: outg_mod.f90
    outheight = H.outheight
    # netCDF variable IDs for main output grid
    specID = []
    specIDppt = []
    wdspecID = []
    ddspecID = []
    # Source: point_mod.90
    ireleasestart = H.ireleasestart
    ireleaseend = H.ireleaseend
    kindz = H.kindz
    xpoint1 = H.xp1
    xpoint2 = H.xp2
    ypoint1 = H.yp1
    ypoint2 = H.yp2
    zpoint1 = H.zpoint1
    zpoint2 = H.zpoint2
    npart = H.npart

    # Create dimensions

    # time
    timeDimID = ncid.createDimension('time', None)
    adate, atime = str(H.ibdate), str(H.ibtime)
    timeunit = 'seconds since ' + adate[:4] + '-' + adate[4:6] + \
        '-'+ adate[6:8] + ' ' + atime[:2] + ':' + atime[2:4]

    # lon
    lonDimID = ncid.createDimension('longitude', nnx)
    # lat
    latDimID = ncid.createDimension('latitude', nny)
    # level
    levDimID = ncid.createDimension('height', nnz)
    # number of species
    nspecDimID = ncid.createDimension('numspec', H.nspec)
    # number of release points   XXX or H.maxpoint?
    pointspecDimID = ncid.createDimension('pointspec', H.numpointspec)
    # number of age classes
    nageclassDimID = ncid.createDimension('nageclass', H.nageclass)
    # dimension for release point characters
    ncharDimID = ncid.createDimension('nchar', 45)
    # number of actual release points
    npointDimID = ncid.createDimension('numpoint', H.numpoint)

    # Create variables

    # time
    tID = ncid.createVariable('time', 'i4', ('time',))
    tID.units = timeunit
    tID.calendar = 'proleptic_gregorian'

    # lon
    lonID = ncid.createVariable('longitude', 'f4', ('longitude',))
    lonID.long_name = 'longitude in degree east'
    lonID.axis = 'Lon'
    lonID.units = 'degrees_east'
    lonID.standard_name = 'grid_longitude'
    lonID.description = 'grid cell centers'

    # lat
    latID = ncid.createVariable('latitude', 'f4', ('latitude',))
    latID.long_name = 'latitude in degree north'
    latID.axis = 'Lat'
    latID.units = 'degrees_north'
    latID.standard_name = 'grid_latitude'
    latID.description = 'grid cell centers'

    # height
    levID = ncid.createVariable('height', 'f4', ('height',))
    # levID.axis = 'Z'
    levID.units = 'meters'
    levID.positive = 'up'
    levID.standard_name = 'height'
    levID.long_name = 'height above ground'

    # RELCOM nf90_char -> dtype = S30
    # http://www.unidata.ucar.edu/mailing_lists/archives/netcdfgroup/2014/msg00100.html
    relcomID = ncid.createVariable('RELCOM', 'S30', ('nchar', 'numpoint'))
    relcomID.long_name = 'release point name'

    # RELLNG1
    rellng1ID = ncid.createVariable('RELLNG1', 'f4', ('numpoint',))
    rellng1ID.units = 'degrees_east'
    rellng1ID.long_name = 'release longitude lower left corner'

    # RELLNG2
    rellng2ID = ncid.createVariable('RELLNG2', 'f4', ('numpoint',))
    rellng2ID.units = 'degrees_east'
    rellng2ID.long_name = 'release longitude upper right corner'

    # RELLAT1
    rellat1ID = ncid.createVariable('RELLAT1', 'f4', ('numpoint',))
    rellat1ID.units = 'degrees_north'
    rellat1ID.long_name = 'release latitude lower left corner'

    # RELLAT2
    rellat2ID = ncid.createVariable('RELLAT2', 'f4', ('numpoint',))
    rellat2ID.units = 'degrees_north'
    rellat2ID.long_name = 'release latitude upper right corner'

    # RELZZ1
    relzz1ID = ncid.createVariable('RELZZ1', 'f4', ('numpoint',))
    relzz1ID.units = 'meters'
    relzz1ID.long_name = 'release height bottom'

    # RELZZ2
    relzz2ID = ncid.createVariable('RELZZ2', 'f4', ('numpoint',))
    relzz2ID.units = 'meters'
    relzz2ID.long_name = 'release height top'

    # RELKINDZ
    relkindzID = ncid.createVariable('RELKINDZ', 'i4', ('numpoint',))
    relkindzID.long_name = 'release kind'

    # RELSTART
    relstartID = ncid.createVariable('RELSTART', 'i4', ('numpoint',))
    relstartID.units = 'seconds'
    relstartID.long_name = 'release start relative to simulation start'

    # RELEND
    relendID = ncid.createVariable('RELEND', 'i4', ('numpoint',))
    relendID.units = 'seconds'
    relendID.long_name = 'release end relative to simulation start'

    # RELPART
    relpartID = ncid.createVariable('RELPART', 'i4', ('numpoint',))
    relpartID.long_name = 'number of release particles'

    # RELXMASS
    relxmassID = ncid.createVariable('RELXMASS', 'f4', ('numpoint', 'numspec'))
    relxmassID.long_name = 'total release particles mass'

    # LAGE
    lageID = ncid.createVariable('LAGE', 'i4', ('nageclass',))
    lageID.units = 'seconds'
    lageID.long_name = 'age class'

    # ORO
    oroID = ncid.createVariable('ORO', 'i4', ('longitude', 'latitude'),
                                chunksizes=(nnx, nny),
                                zlib=True, complevel=complevel)
    oroID.standard_name = 'surface altitude'
    oroID.long_name = 'outgrid surface altitude'
    oroID.units = 'm'

    units = output_units(ncid)

    # Concentration output, wet and dry deposition variables (one per species)
    dIDs = ('longitude', 'latitude', 'height', 'time', 'pointspec', 'nageclass')
    depdIDs = ('longitude', 'latitude', 'time', 'pointspec', 'nageclass')
    chunksizes = (nnx, nny, nnz, 1, 1, 1)
    dep_chunksizes = (nnx, nny, 1, 1, 1)
    for i in range(0, H.nspec):
        anspec = "%3.3d" % (i+1)
        # TODO: iout??, fill lists with values
        # iout: 1 conc. output (ng/m3), 2 mixing ratio (pptv), 3 both,
        # 4 plume traject, 5=1+4
        # Assume iout in (1, 3, 5)
        if True:
            var_name = "spec" + anspec + "_mr"
            sID = ncid.createVariable(var_name, 'f4', dIDs,
                                      chunksizes=chunksizes,
                                      zlib=True, complevel=complevel)
            sID.units = units
            sID.long_name = species[i]
            # sID.decay = decay[i]
            # sID.weightmolar = weightmolar[i]
            # sID.ohreact = ohreact[i]
            # sID.kao = kao[i]
            # sID.vsetaver = vsetaver[i]
            # sID.spec_ass = spec_ass[i]
            # specID[i] = sID  # Index Error because specID is defined as an empty list
            specID.append(sID)
        # Assume iout in (2, 3)
        if True:
            var_name = "spec" + anspec + "_pptv"
            sID = ncid.createVariable(var_name, 'f4', dIDs,
                                      chunksizes=chunksizes,
                                      zlib=True, complevel=complevel)
            sID.units = 'pptv'
            sID.long_name = species[i]
            # sID.decay = decay[i]
            # sID.weightmolar = weightmolar[i]
            # sID.ohreact = ohreact[i]
            # sID.kao = kao[i]
            # sID.vsetaver = vsetaver[i]
            # sID.spec_ass = spec_ass[i]
            # specIDppt[i] = sID
            specIDppt.append(sID)
        # TODO: wetdep?? fill lists with values
        # Assume wetdep is True
        if True:
            var_name = "WD_spec" + anspec
            wdsID = ncid.createVariable(var_name, 'f4', depdIDs,
                                        chunksizes=dep_chunksizes,
                                        zlib=True, complevel=complevel)
            wdsID.units = '1e-12 kg m-2'
            # wdsID.weta = weta[i]
            # wdsID.wetb = wetb[i]
            # wdsID.weta_in = weta_in[i]
            # wdsID.wetb_in = wetb_in[i]
            # wdsID.wetc_in = wetc_in[i]
            # wdsID.wetd_in = wetd_in[i]
            # wdsID.dquer = dquer[i]
            # wdsID.henry = henry[i]
            # wdspecID[i] = wdsID
            wdspecID.append(wdsID)
        # TODO: drydep?? fill lists with values
        # Assume drydep is True
        if True:
            var_name = "DD_spec" + anspec
            ddsID = ncid.createVariable(var_name, 'f4', depdIDs,
                                        chunksizes=dep_chunksizes,
                                        zlib=True, complevel=complevel)
            ddsID.units = '1e-12 kg m-2'
            # dsID.dryvel = dryvel[i]
            # ddsID.reldiff = reldiff[i]
            # ddsID.henry = henry[i]
            # ddsID.f0 = f0[i]
            # ddsID.dquer = dquer[i]
            # ddsID.density = density[i]
            # ddsID.dsigma = dsigma[i]
            # ddspecID[i] = ddsID
            ddspecID.append(ddsID)

    # Fill variables with data.

    # longitudes (grid cell centers)
    coord = []
    for i in range(0, H.numxgrid):
        # coord[i] = ncid.outlon0 + (i - 0.5) * ncid.dxout
        coord.append(ncid.outlon0 + (i - 0.5) * ncid.dxout)
    ncid.variables['longitude'][:] = coord

    # latitudes (grid cell centers)
    coord = []
    for i in range(0, H.numygrid):
        # coord[i] = ncid.outlat0 + (i - 0.5) * ncid.dyout
        coord.append(ncid.outlat0 + (i - 0.5) * ncid.dyout)
    ncid.variables['latitude'][:] = coord

    # levels
    ncid.variables['height'][:] = outheight

    # TODO: write_releases.eqv?
    # Assume write_releases.eqv is True
    if True:
        # release point information
        # TODO: fill lists with values
        for i in range(0, H.numpoint):
            ncid.variables['RELSTART'][i] = ireleasestart[i]
            ncid.variables['RELEND'][i] = ireleaseend[i]
            ncid.variables['RELKINDZ'][i] = kindz[i]
            ncid.variables['RELLNG1'][i] = xpoint1[i]
            ncid.variables['RELLNG2'][i] = xpoint2[i]
            ncid.variables['RELLAT1'][i] = ypoint1[i]
            ncid.variables['RELLAT2'][i] = ypoint2[i]
            ncid.variables['RELZZ1'][i] = zpoint1[i]
            ncid.variables['RELZZ2'][i] = zpoint2[i]
            ncid.variables['RELPART'][i] = npart[i]
            if i <= 1000:
                pass
                # TODO: Fill RELCOM and RELXMASS variables syntax??

    # Age classes
    # TODO: nageclass??
    # Currently H.lage is a 1-element list
    # ncid.variables['LAGE'][:] = lage[0, nageclass]

    # Orography
    # TODO: min_size?? oroout?? assignment syntax?
    # if (not min_size):
        # ncid.variables['ORO'] = 


def create_ncfile(fddir, nested, command_path=None, outdir=None, outfile=None):
    """Main function that create a netCDF4 file from fddir output."""

    print("NESTED:", nested)

    if fddir.endswith('/'):
        # Remove the trailing '/'
        fddir = fddir[:-1]

    H = Header(fddir, nested=nested)

    if H.direction == "forward":
        fprefix = 'grid_conc_'
    else:
        fprefix = 'grid_time_'

    if command_path is None:
        command_path = os.path.join(os.path.dirname(fddir), "options/COMMAND")
    if not os.path.isfile(command_path):
        warnings.warn(
            "The COMMAND file cannot be found.  Continuing without it!")
        command = {}
    else:
        # XXX This needs to be checked out, as I am not sure when the new format
        # started
        try:
            command = read_command(command_path)
        except:
            warnings.warn(
                "The COMMAND file format is not supported.  Continuing without it!")
            command = {}

    if outfile:
        # outfile has priority over previous flags
        ncfname = outfile
    else:
        if outdir is None:
            path = os.path.dirname(fddir)
            fprefix = os.path.join(path, fprefix)
        else:
            fprefix = outdir
        if H.nested:
            ncfname = fprefix + "%s%s" % (H.ibdate, H.ibtime) + "_nest.nc"
        else:
            ncfname = fprefix + "%s%s" % (H.ibdate, H.ibtime) + ".nc"

    cache_size = 16 * H.numxgrid * H.numygrid * H.numzgrid

    ncid = nc.Dataset(ncfname, 'w', chunk_cache=cache_size)
    write_metadata(H, command, ncid)
    write_header(H, command, ncid)
    ncid.close()
    return ncfname


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-n", "--nested",
        help="Use a nested output.",
        action="store_true",
        )
    parser.add_argument(
        "-d", "--dirout",
        help=("The dir where the netCDF4 file will be created. "
              "If not specified, then the fddir/.. is used.")
        )
    parser.add_argument(
        "-o", "--outfile",
        help=("The complete path for the output file. "
              "This overrides the --dirout flag.")
        )
    parser.add_argument(
        "-c", "--command-path",
        help=("The path for the associated COMMAND file. "
              "If not specified, then the fddir/../options/COMMAND is used.")
        )
    parser.add_argument(
        "fddir", nargs="?",
        help="The directory where the FLEXDATA output files are. "
        )
    args = parser.parse_args()

    if args.fddir is None:
        # At least the FLEXDATA output dir is needed
        parser.print_help()
        sys.exit(1)

    ncfname = create_ncfile(args.fddir, args.nested, args.command_path, args.dirout, args.outfile)
    print("New netCDF4 files is available in: '%s'" % ncfname)


if __name__ == '__main__':
    main()

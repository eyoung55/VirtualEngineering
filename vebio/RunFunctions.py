import sys
import os
import contextlib
import subprocess
import glob

import numpy as np
from scipy.interpolate import interp1d

from vebio.FileModifiers import write_file_with_replacements
from vebio.Utilities import yaml_to_dict, dict_to_yaml, check_dict_for_nans


class Feedstock:
    def __init__(self, params_filename, fs_options):
        """Through the ``fs_options`` widgets, the user controls the following
            values:

                * The initial fraction of solids due to xylan (X_X)
                * The initial fraction of solids due to glucan (X_G)
                * The initial porous fraction of the biomass particles

        :param params_filename: (str)
            The filename for the parameters yaml file including
            extension, e.g., ``'virteng_params.yaml'``
        :param fs_options: (WidgetCollection)
            A ``WidgetCollection`` object containing all of widgets used
            to solicit user input for feedstock properties.
        """
        self.params_filename = params_filename
        self._xylan_solid_fraction = fs_options.xylan_solid_fraction.value
        self._glucan_solid_fraction = fs_options.glucan_solid_fraction.value
        self._initial_porosity = fs_options.initial_porosity.widget.value
        self.input2yaml()

    ##############################################
    ### Properties
    ##############################################
    @property
    def xylan_solid_fraction(self):
        return self._xylan_solid_fraction

    @xylan_solid_fraction.setter
    def xylan_solid_fraction(self, a):
        if not 0 <= a <= 1:
            raise ValueError(f"Value {a} is outside allowed interval [0, 1]")
        self._xylan_solid_fraction = float(a)
        self.input2yaml(rewrite=True)

    @property
    def glucan_solid_fraction(self):
        return self._glucan_solid_fraction

    @glucan_solid_fraction.setter
    def glucan_solid_fraction(self, a):
        if not 0 <= a <= 1:
            raise ValueError(f"Value {a} is outside allowed interval [0, 1]")
        self._glucan_solid_fraction = float(a)
        self.input2yaml(rewrite=True)

    @property
    def initial_porosity(self):
        return self._initial_porosity

    @initial_porosity.setter
    def initial_porosity(self, a):
        if not 0 < a < 1:
            raise ValueError(f"Value {a} is outside allowed interval (0, 1)")
        self._initial_porosity = float(a)
        self.input2yaml(rewrite=True)
    ##############################################
    #
    ##############################################

    def input2yaml(self, rewrite=False):
        fs_input = {'xylan_solid_fraction': self._xylan_solid_fraction,
                    'glucan_solid_fraction': self._glucan_solid_fraction,
                    'initial_porosity': self._initial_porosity}
        if rewrite:
            params_dict = yaml_to_dict(self.params_filename)
            params_dict['feedstock'] = fs_input
            dict_to_yaml(params_dict, self.params_filename, merge_with_existing=False)
        else:
            fs_dict = {'feedstock': fs_input}
            dict_to_yaml(fs_dict, self.params_filename)

    def run(self):
        return False

class Pretreatment:

    def __init__(self, notebookDir, params_filename, pt_options):
        """ Through the ``pt_options`` widgets, the user controls the following
            values:

                * Acid Loading (float)
                * Steam Temperature (float)
                * Initial FIS_0 (float)
                * Final Time (float)
                * Show plots (bool)

        :param notebookDir: (str)
            The path to the Jupyter Notebook, used to specify the location
            of the input file and reset the working directory after this operation
            is finished.
        :param params_filename: (str)
            The filename for the parameters yaml file including
            extension, e.g., ``'virteng_params.yaml'``
        :param pt_options: (WidgetCollection) or (dict)
            A ``WidgetCollection`` object containing all of widgets used
            to solicit user input for pretreatment properties.
            or 
            A dictionary containing all input values
        """

        print('Initializing Pretreatment Model')

        self.notebookDir = notebookDir
        self.params_filename = params_filename
        self.show_plots = pt_options.show_plots.value 

        self._initial_acid_conc = pt_options.initial_acid_conc.widget.value
        self._steam_temperature = pt_options.steam_temperature.widget.value + 273.15 # Conversion from celsius to kelvin
        self._initial_solid_fraction = pt_options.initial_solid_fraction.widget.value
        self._final_time = 60 * pt_options.final_time.widget.value
        
        # Obtain steam concentration from lookup table and add to dictionary
        steam_data = np.genfromtxt('pretreatment_model/lookup_tables/sat_steam_table.csv', delimiter=',', skip_header=1)
        # build interpolator interp_steam = interp.interp1d(temp_in_K, dens_in_kg/m3)
        interp_steam = interp1d(steam_data[:, 2], steam_data[:, 4])
        dens = interp_steam(self._steam_temperature)
        # Convert to mol/ml => density in g/L / molecular weight / 1000.0
        mol_per_ml = float(dens/18.01528/1000.0)
        
        self._bulk_steam_conc = mol_per_ml

        # Writing parameters to Yaml file
        self.input2yaml()

        # Move into the pretreatment directory
        os.chdir('pretreatment_model/test/')
        try:    # See if the pretreatment module exists
            import pt
        except: # if not, we need to build it
            print('Could not load PT module, building module from source.')
            print('(This will only happen the first time the notebook is run.)')
            os.chdir('../bld/')
            command = "sh build_first_time.sh"
            subprocess.run(command.split())
            os.chdir('../test/')
            print('Finished building PT module.')
        os.chdir(self.notebookDir)

    ##############################################
    ### Properties
    ##############################################
    @property
    def initial_acid_conc(self):
        return self._initial_acid_conc

    @initial_acid_conc.setter
    def initial_acid_conc(self, a):
        if not 0 <= a <= 1:
            raise ValueError(f"Value {a} is outside allowed interval [0.0, 1.0]")
        self._initial_acid_conc = float(a)
        self.input2yaml(rewrite=True)

    @property
    def steam_temperature(self):
        return self._steam_temperature - 273.15

    @steam_temperature.setter
    def steam_temperature(self, a):
        if not 3.8 <= a <= 250.3:
            raise ValueError(f"Value {a} is outside allowed interval [3.8, 250.3]")
        self._steam_temperature = float(a) + 273.15 # Conversion from celsius to kelvin
        self.input2yaml(rewrite=True)

    @property
    def initial_solid_fraction(self):
        return self._initial_solid_fraction

    @initial_solid_fraction.setter
    def initial_solid_fraction(self, a):
        if not 0 < a < 1:
            raise ValueError(f"Value {a} is outside allowed interval (0, 1)")
        self._initial_solid_fraction = float(a)
        self.input2yaml(rewrite=True)

    @property
    def final_time(self):
        return self._final_time / 60

    @final_time.setter
    def final_time(self, a):
        if not 1 <= a <= 1440:
            raise ValueError(f"Value {a} is outside allowed interval [1, 1440]")
        self._final_time = 60 * float(a)
        self.input2yaml(rewrite=True)

    @property
    def bulk_steam_conc(self):
        return self._bulk_steam_conc

    @bulk_steam_conc.setter
    def bulk_steam_conc(self, a):
        if not 0 < a < 1:  # what are the right values
            raise ValueError(f"Value {a} is outside allowed interval [0, 1]")
        self._bulk_steam_conc = float(a)
        self.input2yaml(rewrite=True)
    ##############################################
    #
    ##############################################

    def input2yaml(self, rewrite=False):
        pt_input = {'initial_acid_conc': self._initial_acid_conc,
                    'steam_temperature': self._steam_temperature,
                    'initial_solid_fraction': self._initial_solid_fraction,
                    'bulk_steam_conc': self._bulk_steam_conc,
                    'final_time': self._final_time}
        if rewrite:
            params_dict = yaml_to_dict(self.params_filename)
            params_dict['pretreatment_input'] = pt_input
            dict_to_yaml(params_dict, self.params_filename, merge_with_existing=False)
        else:
            pt_dict = {'pretreatment_input': pt_input}
            dict_to_yaml(pt_dict, self.params_filename, merge_with_existing=True)

    def run(self, verbose=True):
        """Run pretreatment code specified in pretreatment_model/test/ptrun.py

        :param verbose: (bool, optional) 
            Option to show print messages from executed file, default True.
        """
        print('\nRunning Pretreatment')
        # Move into the pretreatment directory
        os.chdir('pretreatment_model/test/')
        # clear out old data files (`postprocess.py` will pick up longer-run stale data files)
        # TODO: shoud move cleaning in ptrun.py? OD
        outfiles = glob.glob("out*.dat")
        for outfile in outfiles:
            os.remove(outfile)

        import ptrun as pt_run
        # Run pretreatment code specifying location of input file
        path_to_input_file = os.path.join(self.notebookDir, self.params_filename)
        # run_script("ptrun.py", path_to_input_file, verbose=verbose)
        ve_params = pt_run.main(path_to_input_file)
        dict_to_yaml(ve_params, path_to_input_file)
        # unwinding the below because a fix to `f2pymain.f90` now allows rerunning
        # `ptrun.py`; not sure if capturing the output is still wanted, though; JJS
        # 1/13/21
        #pt_run_command = 'python ptrun.py %s' % (path_to_input_file)
        #pt_cli = subprocess.run(pt_run_command.split(), capture_output=True, text=True)
        #print(pt_cli.stdout[-1394:])

        if self.show_plots:
            run_script("postprocess.py", "out_*.dat", "exptdata_150C_1acid.dat", verbose=verbose)

        os.chdir(self.notebookDir)
        print('Finished Pretreatment')

        if check_dict_for_nans(ve_params['pretreatment_output']):
            return True
        return False

class EnzymaticHydrolysis:
    def __init__(self, notebookDir, params_filename, eh_options, hpc_run):
        """ Initialize enzymatic hydrolysis class. Three 
            distinct variants are included in the virtual engineering code:
            (1) a two-phase model which makes a well-mixed assumption, (2)
            a pre-trained surrogate model informed from CFD runs, and (3) 
            the CFD simulation itself, where option (3) is accessible only
            with ``hpc_run=True``. The default unit operation is the 
            surrogate model.

            Through the ``eh_options`` widgets, the user controls the following
            values:

                * Model Type
                * Enzymatic Load (float)
                * FIS_0 Target (float)
                * Final Time (float)
                * Show plots (bool)

        :param notebookDir: (str):
            The path to the Jupyter Notebook, used to specify the location
            of the input file and reset the working directory after this operation
            is finished.
        :param params_filename: (str):
            The filename for the parameters yaml file including
            extension, e.g., ``'virteng_params.yaml'``
        :param eh_options: (WidgetCollection):
            A ``WidgetCollection`` object containing all of widgets used
            to solicit user input for enzymatic hydrolysis properties.
        :param hpc_run: (bool)
            A flag indicating whether or not the Notebook is being
            run on HPC resources, enable CFD only if True.
        """

        print('Initializing Enzymatic Hydrolysis Model')

        self.notebookDir = notebookDir
        self.params_filename = params_filename
        self.hpc_run = hpc_run
        self.show_plots = eh_options.show_plots.value

        # EH input parameters
        self._lambda_e = eh_options.lambda_e.widget.value / 1000   # Conversion from mg/g to kg/kg
        self._fis_0 = eh_options.fis_0.value
        self._t_final = eh_options.t_final.value
        self._model_type = eh_options.model_type.value


        self.ve_params = yaml_to_dict(self.params_filename)
        self.select_run_function()

        # Writing parameters to Yaml file
        self.input2yaml()
        
    ##############################################
    ### Properties
    ##############################################
    @property
    def lambda_e(self):
        return self._lambda_e * 1000 # Conversion from kg/kg to mg/g 

    @lambda_e.setter
    def lambda_e(self, a):
        if not 0 <= a <= 1000:
            raise ValueError(f"Value {a} is outside allowed interval [0, 1000]")
        self._lambda_e = float(a) / 1000 # Conversion from mg/g to kg/kg
        self.input2yaml(rewrite=True)

    @property
    def fis_0(self):
        return self._fis_0

    @fis_0.setter
    def fis_0(self, a):
        if not 0 <= a <= 1:
            raise ValueError(f"Value {a} is outside allowed interval [0, 1]")
        self._fis_0 = float(a)
        self.input2yaml(rewrite=True)

    @property
    def t_final(self):
        return self._t_final

    @t_final.setter
    def t_final(self, a):
        if not 1 <= a <= 24:
            raise ValueError(f"Value {a} is outside allowed interval [1, 24]")
        self._t_final = float(a)
        self.input2yaml(rewrite=True)

    @property
    def model_type(self):
        return self._model_type

    @model_type.setter
    def model_type(self, a):
        if not a in ['CFD Simulation', "CFD Surrogate", 'Lignocellulose Model']:
            raise ValueError("Invalid value. Allowed options: 'CFD Simulation', 'CFD Surrogate', 'Lignocellulose Model'")
        self._model_type = a
        self.input2yaml(rewrite=True)
        self.select_run_function()
    ##############################################
    #
    ##############################################

    def select_run_function(self):
        # selected enzymatic hydrolysis model
        if self._model_type == 'CFD Simulation':
            assert self.hpc_run, f'Cannot run EH_CFD without HPC resources. \n {os.getcwd()}'
            self.run = self.run_eh_cfd_simulation
        elif self._model_type == "CFD Surrogate":
            self.run = self.run_eh_cfd_surrogate
        elif self._model_type == 'Lignocellulose Model':
            self.run = self.run_eh_lignocellulose_model

    def input2yaml(self, rewrite=False):
        eh_input = {'model_type': self._model_type,
                    'lambda_e': self._lambda_e,
                    'fis_0': self._fis_0,
                    't_final': self._t_final}
        if rewrite:
            params_dict = yaml_to_dict(self.params_filename)
            params_dict['enzymatic_input'] = eh_input
            dict_to_yaml(params_dict, self.params_filename, merge_with_existing=False)
        else:
            eh_dict = {'enzymatic_input': eh_input}
            dict_to_yaml(eh_dict, self.params_filename, merge_with_existing=True)

    def get_globalVars(self):
        """ Prepare input values for EH CFD operation

        :return: globalVar dictionary
        """
        # Get FS and PT parameters from yaml file
        self.ve_params = yaml_to_dict(self.params_filename)
        globalVars = {}
        globalVars['fis0'] = self.fix_0
        globalVars['xG0'] = self.ve_params['pretreatment_output']['X_G']
        globalVars['xX0'] = self.ve_params['pretreatment_output']['X_X']
        globalVars['XL0'] = 1.0 - globalVars['xG0'] - globalVars['xX0']
        globalVars['yF0'] = 0.2 + 0.6*self.ve_params['pretreatment_output']['conv']
        globalVars['lmbdE'] = self._lambda_e
        globalVars['rhog0'] = 0.0
        dilution_factor = self._fis_0/self.ve_params['pretreatment_output']['fis_0']
        globalVars['rhox0'] = self.ve_params['pretreatment_output']['rho_x'] * dilution_factor
        globalVars['rhosl0'] = 0.0

        self.dilution_factor = dilution_factor

        return globalVars

    def run_eh_cfd_simulation(self, verbose=True):
        
        print('\nRunning Enzymatic Hydrolysis Model')
        globalVars = self.get_globalVars()
        write_file_with_replacements('constant/globalVars', globalVars)

        # Get reaction_update_time, fluid_update_time, and fluid_steadystate_time
        # in order to convert the user-specified t_final into the endTime definition
        # expected by the OpenFOAM simulation
        reaction_update_time = 1.0
        fluid_update_time = 250.0
        fluid_steadystate_time = 400.0

        with open('constant/EHProperties', 'r') as fp:
            for line in fp:
                if '#' not in line:
                    if 'reaction_update_time' in line:
                        reaction_update_time = float(line.split(']')[-1].split(';')[0])
                    elif 'fluid_update_time' in line:
                        fluid_update_time = float(line.split(']')[-1].split(';')[0])
                    elif 'fluid_steadystate_time' in line:
                        fluid_steadystate_time = float(line.split(']')[-1].split(';')[0])

        controlDict = {}
        fintime = fluid_steadystate_time + (self._t_final/reaction_update_time + 1.0)*fluid_update_time
        controlDict['endTime'] = fintime

        write_file_with_replacements('system/controlDict', controlDict)

        '''
        import numpy as np
        import subprocess
        import os
        
        def check_queue(username, jobname):
            command = 'squeue -u %s -t R,PD -n %s' % (username, jobname)
            out = subprocess.run(command.split(), capture_output=True, text=True)
            print(out.stdout)
            
            if username in out.stdout:
                # Job is running, do nothing
                print('Job is already running')
                job_id = out.stdout.strip().split('\\n')[-1].split()[0]
                
            else:
                # Job is not running, submit it
                command = 'sbatch --job-name=%s dummy_job.sbatch' % (jobname)
                out = subprocess.run(command.split(), capture_output=True, text=True)
                print(out.stdout)
                job_id = out.stdout.strip().split()[-1]
                
                with open('job_history.csv', 'a') as fp:
                    fp.write('%s\\n' % (job_id))
                
            print(job_id, len(job_id))
                
        username = os.environ['USER']
        
        check_queue(username, 'dummy_job')
        '''
        
        # command = "srun hostname"
        # host_list = subprocess.run(command.split(), capture_output=True).stdout.decode()
        # num_nodes = len(host_list)
        # max_cores = int(36*num_nodes)

        username = os.environ['USER']
        jobname = 'eh_cfd'

        command = 'squeue -u %s -t R,PD -n %s' % (username, jobname)
        out = subprocess.run(command.split(), capture_output=True, text=True)

        output_dict = {'enzymatic_output': {}}
        output_dict['enzymatic_output']['rho_g'] = np.nan
        output_dict['enzymatic_output']['rho_x'] = np.nan
        output_dict['enzymatic_output']['rho_sl'] = np.nan
        output_dict['enzymatic_output']['rho_f'] = np.nan

        # TODO: there is no use_previous_output widget in notebook, comment for now 
        # if username in out.stdout:
        #     # Job is running, do nothing
        #     print('EH CFD job is already queued.')
        #     print(out.stdout)
        #     job_id = out.stdout.strip().split('\n')[-1].split()[0]

        #     if eh_options.use_previous_output.value:
        #         print('Using outputs from most recent finished simulation.')
        #         integrated_quantities = np.genfromtxt('old_integrated_quantities.dat') # mol/L
        #         output_dict = {'enzymatic_output': {}}
        #         output_dict['enzymatic_output']['rho_g'] = float(integrated_quantities[-1, -3])
        #         output_dict['enzymatic_output']['rho_x'] = float(integrated_quantities[-1, -2])
        #         output_dict['enzymatic_output']['rho_sl'] = float(integrated_quantities[-1, -1])
        #         output_dict['enzymatic_output']['rho_f'] = float(ve_params['pretreatment_output']['rho_f']*self.dilution_factor)
        #         print('Success.')

        # else:

        # Job is not running, submit it
        print('Submitting EH CFD job.')
        command = 'sbatch --job-name=%s ofoamjob' % (jobname)
        out = subprocess.run(command.split(), capture_output=True, text=True)
        print(out.stdout)
        job_id = out.stdout.strip().split()[-1]
        
        with open('job_history.csv', 'a') as fp:
            fp.write('%s\n' % (job_id))

        print('Job ID = %s' % (job_id))
       
        # Prepare output values from EH CFD operations
        # FIXME: rho_g should be value taken from CFD output - should be good now, please check, JJS 9/15/20
        
        # per Hari's email, glucose concentration in fort.44 is mol/L
        # integrated_quantities = np.genfromtxt('integrated_quantities.dat', delimiter=' ') # mol/L

        '''
        This code represents the conversion that used to be necessary for the NEK 5000 simulation
        outputs, it's preserved here for reference but shouldn't be necessary for the new
        OpenFOAM version of EH.  Although it still may be necessary to calculate a version of
        dilution_factor_final and use it to scale the final four output values.

        rho_g_final = float(c_g_output[-1, 1])*180 # g/L
        
        # back-calculate fis from conversion value
        conv_output = np.genfromtxt('fort.42')
        conversion = float(conv_output[-1,1])
        fis_final = ve_params['enzymatic_input']['fis_0']*(1 - conversion)
        ## if have non-glucan solids, e.g. lignin, then the calculation will be:
        # fis = fis_0*(1 - XG0*conversion)
        ## where XG0 is initial fraction of solids that is glucan
        
        # this dilution calculation is not correct and needs fixing, JJS 9/15/20
        #dilution_factor_final = fis_final/ve_params['enzymatic_input']['fis_0']
        
        # FIXME: dilution_factor_final should be (fis_final)/(ve_params['enzymatic_input']['fis_0'])
        # where fis_final is taken from CFD output
        dilution_factor_final = 1.0
        rho_x_final = rho_x0*dilution_factor_final
        rho_f_final = rho_f0*dilution_factor_final
=
        '''
        
        # output_dict = {'enzymatic_output': {}}
        # output_dict['enzymatic_output']['rho_g'] = integrated_quantities[-1, -3]
        # output_dict['enzymatic_output']['rho_x'] = integrated_quantities[-1, -2]
        # output_dict['enzymatic_output']['rho_sl'] = integrated_quantities[-1, -1]
        # output_dict['enzymatic_output']['rho_f'] = ve_params['pretreatment_output']['rho_f']*dilution_factor
        
        os.chdir(self.notebookDir)
        dict_to_yaml([self.ve_params, output_dict], self.params_filename)
        os.chdir(self.notebookDir)
        print('Finished Enzymatic Hydrolysis')

        if check_dict_for_nans(output_dict):
            return True
        return False

    def run_eh_cfd_surrogate(self, verbose=True):

        print('\nRunning Enzymatic Hydrolysis Model')
        path_to_input_file = os.path.join(self.notebookDir, self.params_filename)

        os.chdir('EH_OpenFOAM/EH_surrogate/')
        from EH_surrogate import main
        ve_params = main(path_to_input_file)

        # run_script("EH_surrogate.py", path_to_input_file, verbose=verbose)
        
        os.chdir(self.notebookDir)
        print('Finished Enzymatic Hydrolysis')

        if check_dict_for_nans(ve_params['enzymatic_output']):
            return True
        return False

    def run_eh_lignocellulose_model(self, verbose=True):
        
        print('\nRunning Enzymatic Hydrolysis Model')
        path_to_input_file = os.path.join(self.notebookDir, self.params_filename)
        os.chdir('two_phase_batch_model/')
        # Commenting out cellulose-only two-phase model to use lignocellulose
        # model, just in case we want to switch back or make both an
        # option. The lignocellulose model is superior.
        #run_script("two_phase_batch_model.py", path_to_input_file, verbose=verbose)
        from driver_batch_lignocell_EH_VE import main
        ve_params = main(path_to_input_file, self.show_plots)

        os.chdir(self.notebookDir)
        print('Finished Enzymatic Hydrolysis')

        if check_dict_for_nans(ve_params['enzymatic_output']):
            return True
        return False

class Bioreactor:
    def __init__(self, notebookDir, params_filename, br_options, hpc_run):
        """ Initialize the aerobic bioreaction operation using 
            user-specified properties. Two distinct models exist: (1) a 
            pre-trained surrogate model informed from CFD runs and (2) the
            full CFD simulation itself where option (2) is accessible only
            with ``hpc_run=True``.  The default option is the surrogate model.

            Through the ``br_options`` widgets, the user controls the following
            values:

                * Model Type
                * Final Time (float)

        :param notebookDir: (str):
            The path to the Jupyter Notebook, used to specify the location
            of the input file and reset the working directory after this operation
            is finished.
        :param params_filename: (str):
            The filename for the parameters yaml file including
            extension, e.g., ``'virteng_params.yaml'``
        :param br_options: (WidgetCollection):
            A ``WidgetCollection`` object containing all of widgets used
            to solicit user input for bioreaction properties.
        :param hpc_run: (bool):
            A flag indicating whether or not the Notebook is being
            run on HPC resources, enable CFD only if True.
        """

        print('Initializing Bioreactor Model')
        self.notebookDir = notebookDir
        self.params_filename = params_filename
        self.hpc_run = hpc_run

        # Bioreactor input parameters
        self._model_type = br_options.model_type.value
        self._gas_velocity = br_options.gas_velocity.value
        self._column_height = br_options.column_height.value
        self._column_diameter = br_options.column_diameter.value
        self._bubble_diameter = br_options.bubble_diameter.value
        self._t_final = br_options.t_final.value

        # Writing input parameters to Yaml file
        self.input2yaml()
        self.select_run_function()

    ##############################################
    ### Properties
    ##############################################
    @property
    def gas_velocity(self):
        return self._gas_velocity

    @gas_velocity.setter
    def gas_velocity(self, a):
        if self._model_type is 'surrogate':
            if not 0.01 <= a <=0.1:
                raise ValueError(f"Value {a} is outside allowed interval [1, 1e16]")
        else: 
            if not 0.0 <= a:
                raise ValueError(f"Value {a} is outside allowed interval [1, 1e16]")
        self._gas_velocity = float(a)
        self.input2yaml(rewrite=True)

    @property
    def column_height(self):
        return self._column_height

    @column_height.setter
    def t_final(self, a):
        if not 10 <= a <= 50:
            raise ValueError(f"Value {a} is outside allowed interval [1, 1e16]")
        self._column_height = float(a)
        self.input2yaml(rewrite=True)

    @property
    def column_diameter(self):
        return self._column_diameter

    @column_diameter.setter
    def column_diameter(self, a):
        if not 1 <= a <= 6:
            raise ValueError(f"Value {a} is outside allowed interval [1, 1e16]")
        self._column_diameter = float(a)
        self.input2yaml(rewrite=True)

    @property
    def bubble_diameter(self):
        return self._bubble_diameter

    @bubble_diameter.setter
    def t_final(self, a):
        if not 0.003 <= a <= 0.008:
            raise ValueError(f"Value {a} is outside allowed interval [1, 1e16]")
        self._bubble_diameter = float(a)
        self.input2yaml(rewrite=True)


    @property
    def t_final(self):
        return self._t_final

    @t_final.setter
    def t_final(self, a):
        if not 1 <= a <= 1e16:
            raise ValueError(f"Value {a} is outside allowed interval [1, 1e16]")
        self._t_final = float(a)
        self.input2yaml(rewrite=True)

    @property
    def model_type(self):
        return self._model_type

    @model_type.setter
    def model_type(self, a):
        if not a in ['CFD Simulation', "CFD Surrogate"]:
            raise ValueError("Invalid value. Allowed options: 'CFD Simulation', 'CFD Surrogate'")
        self._model_type = a
        self.input2yaml(rewrite=True)
        self.select_run_function()
    ##############################################
    #
    ##############################################

    def select_run_function(self):
        # selected enzymatic hydrolysis model
        if self.model_type == 'CFD Simulation':
            assert self.hpc_run, f'Cannot run bioreactor without HPC resources. \n {os.getcwd()}'
            self.run = self.run_biorector_cfd_simulation
        elif self.model_type == "CFD Surrogate":
            self.run = self.run_biorector_cfd_surrogate

    def input2yaml(self, rewrite=False):
        br_input = {'model_type': self._model_type,
                    'gas_velocity': self._gas_velocity,
                    'column_height': self._column_height,
                    'column_diameter': self._column_diameter,
                    'bubble_diameter': self._bubble_diameter,
                    't_final': self._t_final}
        if rewrite:
            params_dict = yaml_to_dict(self.params_filename)
            params_dict['bioreactor_input'] = br_input
            dict_to_yaml(params_dict, self.params_filename, merge_with_existing=False)
        else:
            br_dict = {'bioreactor_input': br_input}
            dict_to_yaml(br_dict, self.params_filename, merge_with_existing=True)

    def run_biorector_cfd_simulation(self, verbose=True):

        print('\nRunning Bioreactor')
        os.chdir('bioreactor/bubble_column/')
        ve_params = yaml_to_dict(self.params_filename)
        # Make changes to the fvOptions file based on replacement options
        fvOptions = {}

        fvOptions['rho_g'] = ve_params['enzymatic_output']['rho_g']
        fvOptions['rho_x'] = ve_params['enzymatic_output']['rho_x']
        fvOptions['rho_f'] = ve_params['enzymatic_output']['rho_f']

        write_file_with_replacements('constant/fvOptions', fvOptions)
        
        # Make changes to the controlDict file based on replacement options
        controlDict = {}
        controlDict['endTime'] = self._t_final
        
        write_file_with_replacements('system/controlDict', controlDict)

        # Run the bioreactor model
        # call function to update ovOptions # fvOptions?
        command = "sbatch ofoamjob"
        subprocess.run(command.split())
            
        output_dict = {'bioreactor_output': {}}
        output_dict['bioreactor_output']['placeholder'] = 123

        os.chdir(self.notebookDir)
        dict_to_yaml(output_dict, self.params_filename, merge_with_existing=True)
        print('Finished Bioreactor')

        if check_dict_for_nans(output_dict):
            return True
        return False

    def run_biorector_cfd_surrogate(self, verbose=True):
        
        print('\nRunning Bioreactor')
        ve_params = yaml_to_dict(self.params_filename)
        if np.isnan(ve_params['enzymatic_output']['rho_g']):
            print('Waiting for EH CFD results.')
        else:
            os.chdir('bioreactor/bubble_column/surrogate_model')
            path_to_input_file = os.path.join(self.notebookDir, self.params_filename)
            from bcolumn_surrogate import main
            ve_params = main(path_to_input_file)
            os.chdir(self.notebookDir)
            print('Finished Bioreactor')

            if check_dict_for_nans(ve_params['bioreactor_output']):
                return True
            return False


def run_script(filename, *args, verbose=True):
    """ Execute the contents of a file.

    This function will attempt to execute the contents of a file specified
    with ``filename`` using the Python ``exec`` function.  No error checking
    is performed on the source file to be executed.

    Args:
        filename (str):
            The filename to execute line by line.
        *args:
            Variable length argument list to be made
            available to the executed file via ``sys.argv[..]``.
        verbose (bool, optional):
            Flag to display the printed outputs
            from the executed file, defaults to ``True``.

    Returns:
        None

    """

    sys.argv = [filename]
    sys.argv.extend(args)
    exec_file = open(filename, 'r')

    if verbose:
        # Execute the file as usual
        exec(exec_file.read(), globals())

    else:
        # Execute the file, redirecting all output to devnull
        # This suppresses any print statements within `filename`
        with open(os.devnull, 'w') as fp:
            with contextlib.redirect_stdout(fp):
                exec(exec_file.read(), globals())

    exec_file.close()
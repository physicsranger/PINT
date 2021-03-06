# parameter.py
# Defines Parameter class for timing model parameters
from ..utils import fortran_float, time_from_mjd_string, time_to_mjd_string,\
    time_to_longdouble, is_number, time_from_longdouble, str2longdouble, \
    longdouble2string, data2longdouble
import numpy
import astropy.units as u
import astropy.time as time
from astropy import log
from pint import pint_units
import astropy.units as u
import astropy.constants as const
from astropy.coordinates.angles import Angle
import re
import numbers
import priors



class Parameter(object):
    """A PINT class describing a single timing model parameter. The parameter
    value will be stored at `value` property in a users speicified format. At
    the same time property `num_value` will store a num value from the value
    and `num_unit` will store the basic unit in the format of `Astropy.units`

    Parameters
    ----------
    name : str, optional
        The name of the parameter.
    value : number, str, `Astropy.units.Quantity` object, or other datatype or
            object
        The current value of parameter. It is the internal storage of
        parameter value
    units : str, optional
        String format for parameter unit
    description : str, optional
        A short description of what this parameter means.
    uncertainty : number
        Current uncertainty of the value.
    frozen : bool, optional
        A flag specifying whether "fitters" should adjust the value of this
        parameter or leave it fixed.
    aliases : list, optional
        An optional list of strings specifying alternate names that can also
        be accepted for this parameter.
    continuous : bool, optional
        A flag specifying whether phase derivatives with respect to this
        parameter exist.
    print_value : method, optional
        A function that converts the internal value to a string for output.
    set_value : method, optional
        A function that sets the value property
    get_num_value:
        A function that get purely value from value attribute
    """

    def __init__(self, name=None, value=None, units=None, description=None,
                 uncertainty=None, frozen=True, aliases=None, continuous=True,
                 print_value=str, set_value=lambda x: x,
                 get_num_value=lambda x: x,
                 prior=priors.Prior(priors.UniformRV()),
                 set_uncertainty=fortran_float):

        self.name = name  # name of the parameter
        self.units = units  # parameter unit in string format,or None
        # parameter num unit, in astropy.units object format.
        # Once it is speicified, num_unit will not be changed.
        self.set_value = set_value
        # Method to get num_value from value
        self.get_num_value = get_num_value
        self.print_value = print_value  # method to convert value to a string.
        self.set_uncertainty = set_uncertainty
        self.value = value  # The value of parameter, internal storage
        self.prior = prior

        self.description = description
        self.uncertainty = uncertainty
        self.frozen = frozen
        self.continuous = continuous
        self.aliases = [] if aliases is None else aliases
        self.is_prefix = False
        self.paramType = 'Parameter'  # Type of parameter. Here is general type
        self.valueType = None

    @property
    def prior(self):
        return self._prior

    @prior.setter
    def prior(self,p):
        if not isinstance(p,priors.Prior):
            log.error("prior must be an instance of Prior()")
        self._prior = p

    # Setup units property
    @property
    def units(self):
        return self._units

    @units.setter
    def units(self, unt):
        # Check if this is the first time set units and check compatable
        if hasattr(self, 'value'):
            if self.units is not None:
                if unt != self.units:
                    wmsg = 'Parameter '+self.name+' units has been reset to '+unt
                    wmsg += ' from '+self._units
                    log.warning(wmsg)
                try:
                    if hasattr(self.value, 'unit'):
                        _ = self.value.to(unt)
                except:
                    log.warning('The value unit is not compatable with'
                                ' parameter units right now.')
    
        # note, _units is a string, _num_unit is the astropy unit

        if unt is None:
            self._units = None
            self._num_unit = None

        elif unt in pint_units.keys():
            # These are special-case unit strings in in PINT
            self._units = unt
            self._num_unit = pint_units[unt]

        else:
            # Try to use it as an astopy unit.  If this fails,
            # ValueError will be raised.
            self._num_unit = u.Unit(unt)
            self._units = self._num_unit.to_string()

        if hasattr(self, 'value') and hasattr(self.value, 'unit'):
            self.value = self.value.to(self.num_unit)
        if hasattr(self, 'uncertainty') and hasattr(self.uncertainty, 'unit'):
            self.uncertainty = self.uncertainty.to(self.num_unit)
            
    # Setup value property
    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, val):
        if val is None:
            if hasattr(self, 'value') and self.value is not None:
                raise ValueError('Setting an exist value to None is not'
                                 ' allowed.')
            else:
                self._value = val
                self._num_value = self._value
                return
        self._value = self.set_value(val)
        self._num_value = self.get_num_value(self._value)

    def prior_pdf(self,value=None, logpdf=False):
        """Return the prior probability, evaluated at the current value of
        the parameter, or at a proposed value.

        Parameters
        ----------
        value : array_like or float_like

        Probabilities are evaluated using the num_value attribute
        """
        if value is None:
            return self.prior.pdf(self.num_value) if not logpdf else self.prior.logpdf(self.num_value)
        else:
            return self.prior.pdf(value) if not logpdf else self.prior.logpdf(value)

    # Setup num_value property
    @property
    def num_value(self):
        return self._num_value

    @num_value.setter
    def num_value(self, val):
        if val is None:
            if not isinstance(self.value, (str, bool)) and \
                self._num_value is not None:
                raise ValueError('This parameter value is number convertable. '
                                 'Setting ._num_value to None will lost the '
                                 'parameter value.')
            else:
                self._num_value = val
                self.value = None

        self._num_value = val
        self._value = self.set_value(val)

    # Setup num_unit property
    @property
    def num_unit(self):
        return self._num_unit

    @property
    def uncertainty(self):
        return self._uncertainty

    @uncertainty.setter
    def uncertainty(self, val):
        if val is None:
            if hasattr(self, 'uncertainty') and self.uncertainty is not None:
                raise ValueError('Setting an exist uncertainty to None is not'
                                 ' allowed.')
            else:
                self._uncertainty = val
                self._num_uncertainty = self._uncertainty
                return
        self._uncertainty = self.set_uncertainty(val)
        self._num_uncertainty = self.get_num_value(self._uncertainty)

    @property
    def num_uncertainty(self):
        return self._num_uncertainty

    @num_uncertainty.setter
    def num_uncertainty(self, val):
        if val is None:
            if not isinstance(self.uncertainty, (str, bool)) and \
                self._num_uncertainty is not None:
                log.warning('This parameter has uncertainty value. '
                            'Change it to None will lost information.')

            self._num_uncertainty = val
            self._uncertainty = val

        elif not isinstance(val, numbers.Number):
            raise ValueError('num_value has to be a pure number or None. ({0} <- {1} ({2})'.format(self.name,val,type(val)))
        else:
            self._num_uncertainty = val
            self._uncertainty = self.set_value(val)


    def __str__(self):
        out = self.name
        if self.units is not None:
            out += " (" + str(self.units) + ")"
        out += " " + self.print_value(self.value)
        if self.uncertainty is not None:
            out += " +/- " + str(self.uncertainty)
        return out

    def set(self, value):

        """Parses a string 'value' into the appropriate internal representation
        of the parameter.
        """
        self.value = value

    def add_alias(self, alias):
        """Add a name to the list of aliases for this parameter."""
        self.aliases.append(alias)

    def help_line(self):
        """Return a help line containing param name, description and units."""
        out = "%-12s %s" % (self.name, self.description)
        if self.units is not None:
            out += ' (' + str(self.units) + ')'
        return out

    def as_parfile_line(self):
        """Return a parfile line giving the current state of the parameter."""
        # Don't print unset parameters
        if self.value is None:
            return ""
        line = "%-15s %25s" % (self.name, self.print_value(self.value))
        if self.uncertainty is not None:
            line += " %d %s" % (0 if self.frozen else 1, str(self.uncertainty))
        elif not self.frozen:
            line += " 1"
        return line + "\n"

    def from_parfile_line(self, line):
        """
        Parse a parfile line into the current state of the parameter.
        Returns True if line was successfully parsed, False otherwise.
        """
        try:
            k = line.split()
            name = k[0].upper()
        except IndexError:
            return False
        # Test that name matches
        if not self.name_matches(name):
            return False
        if len(k) < 2:
            return False
        if len(k) >= 2:
            self.set(k[1])
        if len(k) >= 3:
            try:
                if int(k[2]) > 0:
                    self.frozen = False
                    ucty = '0.0'
            except:
                if is_number(k[2]):
                    ucty = k[2]
                else:
                    errmsg = 'The third column of parfile can only be fitting '
                    errmsg += 'flag (1/0) or uncertainty.'
                    raise ValueError(errmsg)
            if len(k) == 4:
                ucty = k[3]
            self.uncertainty = self.set_uncertainty(ucty)
        return True

    def name_matches(self, name):
        """Whether or not the parameter name matches the provided name
        """
        return (name == self.name) or (name in self.aliases)

class floatParameter(Parameter):
    """This is a Parameter type that is specific to astropy quantity values
    """
    def __init__(self, name=None, value=None, units=None, description=None,
                 uncertainty=None, frozen=True, aliases=None, continuous=True,
                 long_double=False):
        self.long_double = long_double
        if self.long_double:
            set_value = self.set_value_longdouble
            print_value = lambda x: longdouble2string(x.value)
            #get_value = lambda x: data2longdouble(x)*self.num_unit
        else:
            set_value = self.set_value_float
            print_value = lambda x: str(x.value)

        get_num_value = self.get_num_value_float
        set_uncertainty = self.set_value_float
        super(floatParameter, self).__init__(name=name, value=value,
                                             units=units, frozen=True,
                                             aliases=aliases,
                                             continuous=continuous,
                                             description=description,
                                             uncertainty=uncertainty,
                                             print_value=print_value,
                                             set_value=set_value,
                                             set_uncertainty=set_uncertainty,
                                             get_num_value=get_num_value)
        self.value_type = u.quantity.Quantity
        self.paramType = 'floatParameter'


    def set_value_float(self, val):
        """Set value method specific for float parameter
        accept format
        1. Astropy quantity
        2. float
        3. string
        """
        # First try to use astropy unit conversion
        try:
            # If this fails, it will raise UnitConversionError
            _ = val.to(self.num_unit)
            result = val
        except AttributeError:
            # This will happen if the input value did not have units
            result = fortran_float(val) * self.num_unit
            # TODO how to treat num_unit==None ? does it mean 
            # dimensionless or unset?  Ignore for now.. 

        return result

    def set_value_longdouble(self, val):
        try:
            _ = val.to(self.num_unit)
            result = data2longdouble(val.value)*val.unit
        except AttributeError:
            result = data2longdouble(val) * self.num_unit

        return result


    def get_num_value_float(self, val):
        if val is None:
            return None
        else:
            return val.value

class strParameter(Parameter):
    """This is a Parameter type that is specific to string values
    """
    def __init__(self, name=None, value=None, description=None, frozen=True,
                 aliases=[]):
        print_value = str
        get_num_value = lambda x: None
        set_value = self.set_value_str
        set_uncertainty = lambda x: None
        #get_value = self.get_value_str

        super(strParameter, self).__init__(name=name, value=value,
                                           description=None, frozen=True,
                                           aliases=aliases,
                                           print_value=print_value,
                                           set_value=set_value,
                                           get_num_value=get_num_value,
                                           set_uncertainty=set_uncertainty)

        self.paramType = 'strParameter'
        self.value_type = str

    def set_value_str(self, val):
        if hasattr(self,'_num_value') and val == self._num_value:
            raise ValueError('Can not set a num value to a string type'
                             ' parameter.')
        else:
            return str(val)


class boolParameter(Parameter):
    """This is a Parameter type that is specific to boolean values
    """
    def __init__(self, name=None, value=None, description=None, frozen=True,
                 aliases=[]):
        print_value = lambda x: 'Y' if x else 'N'
        set_value = self.set_value_bool
        get_num_value = lambda x: None
        set_uncertainty = lambda x: None
        #get_value = lambda x: log.warning('Can not set a pure value to a '
                                               #'string boolen parameter.')
        super(boolParameter, self).__init__(name=name, value=value,
                                            description=None, frozen=True,
                                            aliases=aliases,
                                            print_value=print_value,
                                            set_value=set_value,
                                            #get_value=get_value,
                                            get_num_value=get_num_value,
                                            set_uncertainty=set_uncertainty)
        self.value_type = bool
        self.paramType = 'boolParameter'

    def set_value_bool(self, val):
        """ This function is to get boolen value for boolParameter class
        """
        if hasattr(self,'_num_value') and val == self._num_value:
            raise ValueError('Can not set a num value to a boolen type'
                             ' parameter.')
        # First try strings
        try:
            return val.upper() in ['Y','YES','T','TRUE','1']
        except AttributeError:
            # Will get here on non-string types
            return bool(val)

class MJDParameter(Parameter):
    """This is a Parameter type that is specific to MJD values."""
    def __init__(self, name=None, value=None, description=None,
                 uncertainty=None, frozen=True, continuous=True, aliases=None,
                 time_scale='utc'):
        self.time_scale = time_scale
        set_value = self.set_value_mjd
        print_value = time_to_mjd_string
        get_num_value = time_to_longdouble
        set_uncertainty = self.set_value_mjd
        super(MJDParameter, self).__init__(name=name, value=value, units="MJD",
                                           description=description,
                                           uncertainty=uncertainty,
                                           frozen=frozen,
                                           continuous=continuous,
                                           aliases=aliases,
                                           print_value=print_value,
                                           set_value=set_value,
                                           #get_value=get_value,
                                           get_num_value=get_num_value,
                                           set_uncertainty=set_uncertainty)
        self.value_type = time.Time
        self.paramType = 'MJDParameter'

    def set_value_mjd(self, val):
        """Value setter for MJD parameter,
           Accepted format:
           Astropy time object
           mjd float
           mjd string
        """
        if isinstance(val, numbers.Number):
            val = numpy.longdouble(val)
            result = time_from_longdouble(val, self.time_scale)
        elif isinstance(val, str):
            try:
                 result = time_from_mjd_string(val, self.time_scale)
            except:
                raise ValueError('String ' + val + 'can not be converted to'
                                 'a time object.' )

        elif isinstance(val,time.Time):
            result = val
        else:
            raise ValueError('MJD parameter can not accept '
                             + type(val).__name__ + 'format.')
        return result


class AngleParameter(Parameter):
    """This is a Parameter type that is specific to Angle values."""
    def __init__(self, name=None, value=None, description=None, units='rad',
             uncertainty=None, frozen=True, continuous=True, aliases=None):
        self.unit_identifier = {
            'h:m:s': (u.hourangle, 'h', '0:0:%.15fh'),
            'd:m:s': (u.deg, 'd', '0:0:%.15fd'),
            'rad': (u.rad, 'rad', '%.15frad'),
            'deg': (u.deg, 'deg', '%.15fdeg'),
        }
        # Check unit format
        if units.lower() not in self.unit_identifier.keys():
            raise ValueError('Unidentified unit ' + units)

        self.unitsuffix = self.unit_identifier[units.lower()][1]
        set_value = self.set_value_angle
        print_value = lambda x: x.to_string(sep=':', precision=8) \
                        if x.unit != u.rad else x.to_string(decimal = True,
                        precision=8)
        #get_value = lambda x: Angle(x * self.unit_identifier[units.lower()][0])
        get_num_value = lambda x: x.value
        set_uncertainty = self.set_uncertainty_angle
        self.value_type = Angle
        self.paramType = 'AngleParameter'

        super(AngleParameter, self).__init__(name=name, value=value,
                                             units=units,
                                             description=description,
                                             uncertainty=uncertainty,
                                             frozen=frozen,
                                             continuous=continuous,
                                             aliases=aliases,
                                             print_value=print_value,
                                             set_value=set_value,
                                             #get_value=get_value,
                                             get_num_value=get_num_value,
                                             set_uncertainty=set_uncertainty)

    def set_value_angle(self, val):
        """ This function is to set value to angle parameters.
        Accepted format:
        1. Astropy angle object
        2. float
        3. number string
        """
        if isinstance(val, numbers.Number):
            result = Angle(val * self.num_unit)
        elif isinstance(val, str):
            try:
                result = Angle(val + self.unitsuffix)
            except:
                raise ValueError('Srting ' + val + ' can not be converted to'
                                 ' astropy angle.')
        elif isinstance(val, Angle):
            result = val.to(self.num_unit)
        else:
            raise ValueError('Angle parameter can not accept '
                             + type(val).__name__ + 'format.')
        return result

    def set_uncertainty_angle(self, val):
        """This function is to set the uncertainty for an angle parameter.
        """
        if isinstance(val, numbers.Number):
            result =Angle(self.unit_identifier[self.units.lower()][2] % val)
        elif isinstance(val, str):

            result =Angle(self.unit_identifier[self.units.lower()][2] \
                          % fortran_float(val))
            #except:
            #    raise ValueError('Srting ' + val + ' can not be converted to'
            #                     ' astropy angle.')
        elif isinstance(val, Angle):
            result = val.to(self.num_unit)
        else:
            raise ValueError('Angle parameter can not accept '
                             + type(val).__name__ + 'format.')
        return result

class prefixParameter(Parameter):
    """ This is a Parameter type for prefix parameters, for example DMX_

        Create a prefix parameter
        To create a prefix parameter, there are two ways:
        1. Create by name
            If optional agrument name with a prefixed format, such as DMX_001
            or F10, is given. prefixParameter class will figure out the prefix
            name, index and indexformat.
        2. Create by prefix and index
            This method allows you create a prefixParameter class using prefix
            name and index. The class name will be returned as prefix name plus
            index with the right index format. So the optional arguments
            prefix, indexformat and index are need. index default value is 1.
        If both of two methods are fillfulled, It will using the first method.
        Add descrition and units.
        1. Direct add
            A descrition and unit can be added directly by using the optional
            arguments, descrition and units. Both of them will return as a
            string attribution.
        2. descrition and units template.
            If the descrition and unit are changing with the prefix parameter
            index, optional argurment descritionTplt and unitTplt are need.
            These two attributions are lambda functions, for example
            >>> descritionTplt = lambda x: 'This is the descrition of parameter
                                            %d'%x
            The class will fill the descrition and unit automaticly.
        If both two methods are fillfulled, it prefer the first one.

        Parameter
        ---------
        name : str optional
            The name of the parameter. If it is not provided, the prefix and
            index format are needed.
        prefix : str optional
            Paremeter prefix, now it is only supporting 'prefix_' type and
            'prefix0' type.
        indexformat : str optional
            The format for parameter index
        index : int optional [default 1]
            The index number for the prefixed parameter.
        units :  str optional
            The unit of parameter
        unitTplt : lambda method
            The unit template for prefixed parameter
        description : str optional
            Description for the parameter
        descriptionTplt : lambda method optional
            Description template for prefixed parameters
        prefix_aliases : list of str optional
            Alias for the prefix
        frozen : bool, optional
            A flag specifying whether "fitters" should adjust the value of this
            parameter or leave it fixed.
        continuous : bool
        type_match : str, optinal, default 'float'
            Example paramter class template for value and num_value setter
        long_double : bool, optional default 'double'
            Set float type value and num_value in numpy float128
        time_scale : str, optional default 'utc'
            Time scale for MJDParameter class.
    """

    def __init__(self, name=None, prefix=None, indexformat=None, index=1,
                 value=None, units=None, unitTplt=None,
                 description=None, descriptionTplt=None,
                 uncertainty=None, frozen=True, continuous=True,
                 prefix_aliases=[], type_match='float', long_double=False,
                 time_scale='utc'):
        # Create prefix parameter by name
        if name is None:
            if prefix is None or indexformat is None:
                errorMsg = 'When prefix parameter name is not give, the prefix'
                errorMsg += 'and indexformat are both needed.'
                raise ValueError(errorMsg)
            else:
                # Get format fields
                digitLen = 0
                for i in range(len(indexformat)-1, -1, -1):
                    if indexformat[i].isdigit():
                        digitLen += 1
                self.indexformat_field = indexformat[0:len(indexformat)
                                                     - digitLen]
                self.indexformat_field += '{0:0' + str(digitLen) + 'd}'

                name = prefix+self.indexformat_field.format(index)
                self.prefix = prefix
                self.indexformat = self.indexformat_field.format(0)
                self.index = index
        else:  # Detect prefix and indexformat from name.
            namefield = re.split('(\d+)', name)
            if len(namefield) < 2 or namefield[-2].isdigit() is False\
               or namefield[-1] != '':
            #When Name has no index in the end or no prefix part.
                errorMsg = 'Prefix parameter name needs a perfix part'\
                           + ' and an index part in the end. '
                errorMsg += 'If you meant to set up with prefix, please use' \
                            + 'prefix and indexformat optional agruments.' \
                            + 'Leave name argument alone.'
                raise ValueError(errorMsg)
            else:  # When name has index in the end and prefix in front.
                indexPart = namefield[-2]
                prefixPart = namefield[0:-2]
                self.indexformat_field = '{0:0' + str(len(indexPart)) + 'd}'
                self.indexformat = self.indexformat_field.format(0)
                self.prefix = ''.join(prefixPart)
                self.index = int(indexPart)

        # Set up other attributes
        self.unit_template = unitTplt
        self.description_template = descriptionTplt
        # set templates
        if self.unit_template is None:
            self.unit_template = lambda x: self.units
        if self.description_template is None:
            self.description_template = lambda x: self.descrition
        # Using other parameter class as a template for value and num_value
        # setter
        self.type_identifier = {
                               'float': (floatParameter, {'units' : '',
                                         'long_double' : False,
                                         'uncertainty' : 0.0 }),
                               'string': (strParameter, {}),
                               'bool': (boolParameter, {}),
                               'mjd': (MJDParameter, {'time_scale' : 'utc',
                                       'uncertainty' : 0.0}),
                               'angle': (AngleParameter, {'units' : 'rad',
                                         'uncertainty' : 0.0})}

        if isinstance(type_match, str):
            self.type_match = type_match.lower()
        elif isinstance(value_type, type):
            self.type_match = type_match.__name__
        else:
            self.type_match = type(type_match).__name__

        if self.type_match not in self.type_identifier.keys():
            raise ValueError('Unrecognized value type ' + self.type_match)

        print_value = self.print_value_prefix
        set_value = self.set_value_prefix
        #get_value = self.get_value_prefix
        get_num_value = self.get_num_value_prefix
        set_uncertainty = self.set_uncertainty_prefix
        self.time_scale = time_scale
        self.long_double = long_double
        super(prefixParameter, self).__init__(name=name, value=value,
                                              units=units,
                                              description=description,
                                              uncertainty=uncertainty,
                                              frozen=frozen,
                                              continuous=continuous,
                                              print_value=print_value,
                                              set_value=set_value,
                                              #get_value=get_value,
                                              get_num_value=get_num_value,
                                              set_uncertainty=set_uncertainty)

        self.prefix_aliases = prefix_aliases
        self.is_prefix = True

    def prefix_matches(self, prefix):
        return (prefix == self.perfix) or (prefix in self.prefix_aliases)

    def apply_template(self):
        dsc = self.description_template(self.index)
        self.description = dsc
        unt = self.unit_template(self.index)
        self.units = unt

    def get_par_type_object(self):
        par_type_class = self.type_identifier[self.type_match][0]
        obj = par_type_class('example')
        attr_dependency = self.type_identifier[self.type_match][1]
        for dp in attr_dependency.keys():
            if hasattr(self, dp):
                prefix_arg = getattr(self, dp)
                setattr(obj, dp, prefix_arg)
        return obj

    def set_value_prefix(self, val):
        obj = self.get_par_type_object()
        result = obj.set_value(val)
        return result

    def get_value_prefix(self, val):
        obj = self.get_par_type_object()
        result = obj.get_value(val)
        return result

    def get_num_value_prefix(self, val):
        obj = self.get_par_type_object()
        result = obj.get_num_value(val)
        return result

    def print_value_prefix(self, val):
        obj = self.get_par_type_object()
        result = obj.print_value(val)
        return result

    def set_uncertainty_prefix(self, val):
        obj = self.get_par_type_object()
        result = obj.set_uncertainty(val)
        return result

    def new_index_prefix_param(self, index):
        """Get one prefix parameter with the same type.
        Parameter
        ----------
        index : int
            index of prefixed parameter.
        Return
        ----------
        A prefixed parameter with the same type of instance.
        """
        newpfx = prefixParameter(prefix=self.prefix,
                                 indexformat=self.indexformat, index=index,
                                 unitTplt=self.unit_template,
                                 descriptionTplt=self.description_template,
                                 frozen=self.frozen,
                                 continuous=self.continuous,
                                 type_match=self.type_match,
                                 long_double=self.long_double,
                                 time_scale=self.time_scale)
        newpfx.apply_template()
        return newpfx

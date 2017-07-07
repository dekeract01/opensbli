"""
# Imports required are
from .opensbliobjects impot *
from sympy import the following
a. Sum
b. get_contraction_structure
c. get_indices
d. EXPR
_remove_repeated
"""
from sympy import *
from sympy.tensor import *
from sympy.tensor.index_methods import _remove_repeated
from .opensbliobjects import *
from sympy.functions.elementary.piecewise import ExprCondPair
# from .bcs import apply_modify_derivative
from numpy import ndindex as mutidimindex
from sympy.functions.special.tensor_functions import eval_levicivita

#ndim = 2 # Testing change this
def summation_apply(final_expr, sumindices):
    for k in sumindices:
        final_expr = Sum(final_expr, (k,0, Symbol('ndim', integer=True)))

    return final_expr

def expand_expr(expr, ndim):
    sumindices = expr.variables
    input_expr = expr.function
    # Expansion
    expanded_expr = 0
    #pprint([input_expr, sumindices])
    for no, k in enumerate(sumindices):
        if no == 0:
            expanded_expr = 0
            input_expr = input_expr
        else:
            input_expr = expanded_expr
            expanded_expr = 0 #  now do the expansion of the expanded expression
        for dim in range(ndim):
            dictionary = {}
            for at in input_expr.atoms(EinsteinTerm):
                dictionary[at] = at.apply_index(k, dim)
            expanded_expr += input_expr.xreplace(dictionary)
    #pprint(expanded_expr)
    return expanded_expr

def expand_free_indices(expr, indices, ndim):
    shape = tuple([ndim for i in indices])
    out = []#[expr for i in range(ndim**len(indices))]
    it = mutidimindex(shape)
    indices = list(indices)
    for i in it:
        local_expr = expr.copy()
        local_map = []
        linear_index = 0
        for no in range(len(indices)):
            local_map += [(indices[no], i[no])]
            #linear_index += ndim*i[no]
        for at in local_expr.atoms(EinsteinTerm):
            evaluated = at.apply_multiple_indices(indices, local_map)
            local_expr = local_expr.replace(at, evaluated)

        out += [local_expr]
    return out

class KD(Function):
    """ Handler for the built-in SymPy KroneckerDelta function. """

    @property
    def is_commutative(self):
        return False

    def structure(self):
        """
        No Contraction structure for the KD function
        """
        indices = flatten([p.get_indices() for p in self.args if p.get_indices])
        indexed = IndexedBase("%s"%self.__class__.__name__)
        indexed = indexed[indices]
        indexed.expression = self
        indexed.is_commutative = False
        return indexed
    
    def value(self):
        if len(self.args) != 2:
            raise ValueError("Expected only two arguments in KD.")
        if Symbol(str(self.args[0])) == Symbol(str(self.args[1])):
            return S.One
        else:
            return S.Zero
        

class LC(Function):
    """ Handler for the built-in SymPy LeviCivita function. """

    @property
    def is_commutative(self):
        return False
    def structure(self):
        if len(self.args) != 3:
            raise ValueError("LeviCivita function should have only three indices.")

        indices = flatten([p.get_indices() for p in self.args if p.get_indices])
        indexed_base = IndexedBase("%s"%self.__class__.__name__)
        indexed = indexed_base[tuple(indices)]
        indexed.expression = self
        indexed.is_commutative = False
        return indexed
    
    def value(self):
        args = []
        for a in self.args:
            if isinstance(a, EinsteinTerm):
                if not a.get_base():
                    args += Symbol(str(a))
            else:
                args += [a]
        return eval_levicivita(*args)

class EinsteinStructure(object):
    def apply_contraction(cls, contraction_dictionary, expr, reversesubs):
        outer = []
        replacements = {}
        # Traverse the contraction structure
        def _contraction_traverse(d1, outer, replacements):
            for key in d1:
                if isinstance(key,Expr):
                    continue
                for term in d1[key]:
                    if term in d1:
                        for term1 in d1[term]:
                            _contraction_traverse(term1, outer, replacements)
                if key:
                    for val in d1[key]:
                        summation_notation = val
                        summation_notation = summation_apply(summation_notation, key)
                        #for k in key:
                            #summation_notation = Sum(summation_notation, (k,0, Symbol('ndim', integer=True)))
                        if val in replacements:
                            print (exist)
                            raise ValueError("The replacement object already exist this might cause errors")
                        summation_notation = summation_notation.xreplace(replacements)
                        replacements[val] = summation_notation
                    outer += [tuple([key, d1[key]])]

            return replacements, outer
        replacements, outer = _contraction_traverse(contraction_dictionary, outer, replacements)
        expr = expr.subs(replacements)
        return expr

    def _structure(cls, expr):
        substits = {}
        value1 = expr
        obj_substitutions = {}
        pot = preorder_traversal(expr)
        # Find the structure of individual local functions in the given expression
        reversesubs = {}
        for p in pot:
            if isinstance(p, localfuncs):
                if p.structure():
                    substits[p] = p.structure()
                    expr = expr.xreplace({p: substits[p]})
                else:
                    pass
                pot.skip()
            elif isinstance(p, local_objects):
                if p.structure():
                    obj_substitutions[p] = p.structure()
                else:
                    pass
                pot.skip()
            elif(isinstance(p, Derivative)):
                pprint(p)
                raise ValueError("This derivative is not classified", p)
            else:
                continue
        # Store the expressions for the indexed objects as they need to
        #pprint(substits)
        #pprint(expr)
        expr = expr.xreplace(obj_substitutions)
        #pprint(expr)
        #for key,val in substits.iteritems():
            #pprint([key,val, val.expression])
            #reversesubs[val] = val.expression
        #pprint(reversesubs)
        # get the contraction structure of the expression
        #print(expr)
        contraction_dictionary = (get_contraction_structure(expr))
        indices, dummies = get_indices(expr)
        #pprint(["BEFORE APPLY",expr])
        expr = cls.apply_contraction(contraction_dictionary, expr, reversesubs)
        #pprint(expr)
        return expr, indices
    def substitute_indexed(cls,indexedexpr):
        pot = preorder_traversal(indexedexpr)
        indexed_subs = {}
        indexedBaseSubs = {}
        einsteinobjectsubs = {}
        # pprint(indexedexpr)

        #for at in indexedexpr.atoms(EinsteinTerm):
            #einsteinobjectsubs[at] = at.expression

        for p in pot:
            if isinstance(p, Indexed):
                indexed_subs[p] = p.expression
                #pprint([p, p.expression])
                pot.skip()
            elif isinstance(p, IndexedBase):
                indexedBaseSubs[p] = p.expression
                pot.skip()
            else:
                continue

        # now substitute them in the original expression
        indexedexpr = indexedexpr.xreplace(indexed_subs)
        indexedexpr = indexedexpr.xreplace(indexedBaseSubs)

        return indexedexpr
    def expand_summations(cls, expression, ndim):
        #pprint(expression.atoms(Sum))
        # To expand the summation notation. Do a postorder traversal of the tree
        pot = postorder_traversal(expression)
        to_expand = []
        for p in pot:
            if isinstance(p, Sum):
                to_expand += [p]
        # Once we have the terms to be expanded

        expansion_subs = {}
        for no, val in enumerate(to_expand):
            value = val.subs(expansion_subs)
            if isinstance(value, Sum):
                expansion_subs[val] = expand_expr(value, ndim)
            else:
                expansion_subs[val] = value
        # Do a pre_order traversal and substitute the values in the original expression
        pot = preorder_traversal(expression)
        for p in pot:
            if isinstance(p, Sum):
                #pprint(p,)
                expression = expression.xreplace({p:expansion_subs[p]})
                pot.skip()
            else:
                continue
        return expression

class BasicDiscretisation(EinsteinStructure):
    @property
    def required_datasets(cls):
        """By the time this function is called all the functions such as
        KD, LC, DOT etc.. should be evaluated
        """
        objs = list(cls.args[0].atoms(DataSet))
        return objs
    @property
    def required_datasetbases(cls):
        objs = list(cls.args[0].atoms(DataSetBase)) + list(cls.work.atoms(DataSetBase))
        return list(set(objs))
    @property
    def required_constants(cls):
        constants = list(cls.args[0].atoms(ConstantObject))
        return constants
    @property
    def required_functions(cls):
        """
        this should return the functions if any in the expression
        """
        subeval = []
        if cls.args[0].atoms(Function):
            raise ValueError("Argument zero of derivative contains nested ders")
        if cls.is_homogeneous:
            pass
        else:
            subclasstypes = len(cls.args) - 2
            for n in range(subclasstypes):
                newargs = [cls.args[0]] + [cls.args[n+1]]
                subeval += [type(cls)(*newargs)]
        return subeval
    @property
    def order(cls):
        coordinates = len(cls.atoms(CoordinateObject))
        #pprint([cls, coordinates])
        return len(cls.args)-1
    @property
    def is_homogeneous(cls):
        if len(set(cls.args[1:])) == 1:
            return True
        else:
            return False
    @property
    def is_store(cls):
        if hasattr(cls, 'store'):
            return cls.store
        else:
            return False
    @property
    def get_direction(cls):
        direction = []
        for args in cls.args[1:]:
            direction += [args.direction]
        return direction
    @property
    def _sanitise(cls):
        """ As of now CD(u0,x0,x1) --> CD(CD(u0,x0), x1)
        need a better formulation"""
        args = [cls.args[0], cls.args[1]]
        expr = type(cls)(*args)
        for arg in cls.args[2:]:
            args = [expr, arg]
            expr = type(cls)(*args)
        return expr
    @property
    def used_else_where(self):
        if hasattr(self, '_is_used'):
            return self._is_used
        else:
            return False
    def is_used(self, value):
        self._is_used = value
        return
    def update_work(cls, block):
        """
        For this we set the indices of the work array to be same as that of
        the derivaitve indices. This way no mapping is required.
        Block work array will be implemented
        """
        cls.work = block.work_array()
        block.increase_work_index
        return

    def set_store(cls, value):
        cls.store = value
        return

    def hashs(cls, outer_structure=None):
        if outer_structure:
            tup = (cls.args + tuple(list(outer_structure)))
        else:
            tup = cls.args
        return hash((type(cls).__name__,) + tup)

    def structure(cls):
        """ calls the _structure function which returns the summation notation"""
        local_structure = []
        for arg in cls.args:
            #pprint(arg)
            expr, outer_indices = cls._structure(arg)
            local_structure += [(expr, outer_indices)]
        """
        # Process the outer indices structure for the derivatives
        this involves removing repeated indices of all args and applying summation convention on the dummy indices
        all_outer_inds = []
        expr_args = []
        for ind in local_structure:
            a, b = ind
            expr_args += [a]
            all_outer_inds += list(b)
        final_expr = type(cls)(*expr_args)
        temporary_indexed_object = IndexedBase("temp", *all_outer_inds)
        inds, summations = _remove_repeated(temporary_indexed_object)
        if summations:
            for k in summations:
                final_expr = Sum(final_expr, (k,0, Symbol('ndim', integer=True)))
        """
        all_outer_inds = []
        expr_args = []
        for ind in local_structure:
            a, b = ind
            #pprint([a,list(b)])
            expr_args += [a]
            all_outer_inds += list(b)
        final_expr = type(cls)(*expr_args)
        if all_outer_inds:
            temporary_indexed_object = IndexedBase("temp")[all_outer_inds]
            inds, summations = _remove_repeated(temporary_indexed_object.indices)
        else:
            summations = None
            inds = None
        if summations:
            final_expr = summation_apply(final_expr, summations)
        if inds:
            indexedobj = IndexedBase("%s%s"%(cls.simple_name, cls.hashs(inds)))[tuple(inds)]
        else:
            indexedobj = IndexedBase("%s%s"%(cls.simple_name, cls.hashs()))
        final_expr = cls.substitute_indexed(final_expr)
        indexedobj.expression = final_expr
        #pprint(["EXPRESSION", cls,indexedobj, indexedobj.expression ])
        return indexedobj

class Dot(Function, BasicDiscretisation):

    def __new__(cls, arg1, arg2):
        ret = super(Dot, cls).__new__(cls, arg1, arg2)
        return ret
    #def structure(cls):
        #"""
        #This function is not dependant on _strcture
        #"""
        #indices = flatten([p.get_indices() for p in cls.args if p.get_indices])
        #hashs = str(hash((type(cls).__name__,) + cls.args ))
        #indexed = IndexedBase("%s%s"%(cls.__class__.__name__, hashs))
        #indexed.expression = cls
        #return
    @property
    def simple_name(self):
        return "Dot"
    @property
    def value(self):
        return Mul(*self.args)

"""
The structure for einstein expansion would be the following,
a. All the derivatives etc etc are converted into structure's
CD, WD, TD, DObj, COordobj, ConstantObject --> .structure should give the structure
CD, WD, TD/ Expression, KD, LC, DOT etc --> .structure
._structure gives you an expression with summation objects,
in the local/self/cls we apply the outer structure like for Derivative(u_j,x_j) should be an IndexedBase with no
indices

Each indexed object should have
a. indexedexpr in summation notation
b. Summation notation in original expression

"""

""" All the evaluations are in respective classes
a. Requires
b. Subevals
c. subderivatives
d. set_store
e. update the work arrays
f. Create computations
g. Update the original equations
"""
from opensbli.utilities.helperfunctions import get_inverse_deltas
class CentralDerivative(Function, BasicDiscretisation):
    """
    wrapper class to represent derivatives
    Sympy already have a "Derivative" class, thus double D
    """
    #nargs = (2,3,4,5,6,7)
    def __new__(cls, expr, *args):
        args = tuple(flatten([expr] + list(args)))
        ret = super(CentralDerivative, cls).__new__(cls, *args, evaluate=False)
        ret.store = True # By default all the derivatives are stored
        ret.local_evaluation = True
        return ret

    def doit(cls):
        #print [arg==S.Zero for arg in cls.args]
        if any(arg == S.Zero for arg in cls.args):
            return S.Zero
        elif len(set(cls.args)) == 1:
            return S.One
        else:
            return cls

    def _discretise_derivative(cls, scheme, block, boundary=True):
        """This would return the descritised derivative of the
        local object depending on the order of accuracy specified
        Returns the formula for the derivative function, only first derivatives or homogeneous
        derivatives of higher order are supported. The mixed derivatives will be handled impl-
        citly while creating the kernels
        :arg derivative: the derivative on which descritisation should be performed
        :returns: the descritised derivative, in case of wall boundaries this is a Piecewise-
        function
        """
        order = cls.order
        form = 0
        # Put the coefficients of first and second derivatives in a dictionary and use them
        if cls.is_homogeneous:
            dire = cls.get_direction[0]
            weights = scheme._generate_weights(dire, order, block)
            for no, p in enumerate(scheme.points):
                expr = cls.args[0]
                for req in (cls.required_datasets):
                    loc = list(req.indices)
                    loc[dire] = loc[dire] + p
                    val = req.base[loc]
                    expr = expr.replace(req, val)
                form = form + weights[no]*expr
            if form == 0:
                raise ValueError("Central derivative formula is zero for %s"%cls)
        else:
            raise ValueError("The provided derivative is not homogeneous, %s"%cls)
        if boundary:
            form = cls.modify_boundary_formula(form, block)

        delta = S.One/block.deltas[dire]**order
        inv_delta = get_inverse_deltas(delta)
        form = form*(inv_delta)
        return form

    def modify_boundary_formula(cls, form, block):
        # Apply the boundary modifications
        modifications = block.check_modify_central()
        dire = cls.get_direction[0]
        if dire in modifications:
            #print "YES", dire, cls
            boundary_mods = [k for k in modifications[dire] if k]
            expression_condition_pairs = []
            pprint(cls.args[0])
            for b in boundary_mods:
                expression_condition_pairs += b.modification_scheme.expr_cond_pairs(cls.args[0], b.direction, b.side, cls.order, block)
            expression_condition_pairs += [ExprCondPair(form, True)]
            form  = Piecewise(*expression_condition_pairs, **{'evaluate':False})
        return form
    def apply_boundary_derivative_modification(cls, block, scheme, work):
        """Apply the boundary modifications this returns a list of kernels if modification
        is required else returns an empty list
        WARNING This is not working but keeping it while reverting back
        """
        from opensbli.core.kernel import Kernel
        dire = cls.get_direction[0]
        order = cls.order
        modifications = block.check_modify_central()
        kernels = []
        if dire in modifications:
            #print "YES", dire, cls
            boundary_mods = [k for k in modifications[dire] if k]
            pprint(cls.args[0])
            for b in boundary_mods:
                ker = Kernel(block)
                ker.add_equation(expr)
                ker.set_computation_name("Carpenter scheme %s "%(str(cls)))
                ker.set_grid_range(block)
                # modify the range to the number of points
                expression_condition_pairs, ranges = b.modification_scheme.expr_cond_pairs(cls.args[0], b.direction, b.side, order, block)
                ker.ranges[dire] = [ranges[0], ranges[-1]+1]
                #expression_condition_pairs += b.modification_scheme.expr_cond_pairs(cls.args[0], b.direction, b.side, order, block)
                expression_condition_pairs += [ExprCondPair(0, True)]
                form  = Piecewise(*expression_condition_pairs, **{'evaluate':False})
                ker.add_equation(Eq(work, form))
                kernels += [ker]
        return kernels
    @property
    def simple_name(cls):
        return "%s"%("CD")
    def _sympystr(self, p):
        args = list(map(p.doprint, self.args))
        return "%s %s"%(self.simple_name, " ".join(args))

    def classical_strong_differentiabilty_transformation(cls, metric):
        direction = cls.get_direction
        if cls.order == 1:
            metric_der = metric.classical_strong_differentiabilty_transformation[direction[0]]
            transformed_der = metric_der.subs(metric.general_function, cls.args[0])
        elif cls.order == 2:
            metric_der = metric.classical_strong_differentiabilty_transformation_sd[tuple(cls.get_direction)]
            transformed_der = metric_der.subs(metric.general_function, cls.args[0])

        return transformed_der

class WenoDerivative(Function, BasicDiscretisation):

    def __new__(cls, expr, *args):
        args = flatten([expr] + list(args))
        ret = super(WenoDerivative, cls).__new__(cls, *args, evaluate=False)
        ret.store = True # By default all the derivatives are stored
        ret.reconstructions = []
        ret.local_evaluation = True
        return ret
    @property
    def simple_name(cls):
        return "%s"%("WD")

    def _discretise_derivative(cls, block, scheme=None):
        """This would return the descritised derivative of the
        local object depending on the order of accuracy specified
        Returns the formula for the derivative function, only first derivatives or homogeneous
        derivatives of higher order are supported. The mixed derivatives will be handled impl-
        citly while creating the kernels
        :arg derivative: the derivative on which descritisation should be performed
        :returns: the descritised derivative, in case of wall boundaries this is a Piecewise-
        function
        """
        order = cls.order
        if (order > 1):
            raise ValueError("Weno Derivatives only defined for first order")
        dire = cls.get_direction[0]
        delta = block.deltas[dire]
        loc = list(cls.reconstruction_work.indices[:])
        loc[dire] += -1
        form = (cls.reconstruction_work - cls.reconstruction_work.base[loc]) / delta
        return form

    def add_reconstruction_classes(self, classes):
        if isinstance(classes, list):
            self.reconstructions += classes
        else:
            self.reconstructions += [classes]
        return
    def create_reconstruction_work_array(self, block):
        self.reconstruction_work = block.work_array()
        block.increase_work_index
        return
    @property
    def evaluate_reconstruction(self):

        total = 0
        for r in self.reconstructions:
            total += r.reconstructed_symbol
        return total
    def _sympystr(self, p):
        args = list(map(p.doprint, self.args))
        return "%s %s"%(self.simple_name, " ".join(args))

    def classical_strong_differentiabilty_transformation(cls, metric):
        direction = cls.get_direction
        if cls.order == 1:
            metric_der = metric.classical_strong_differentiabilty_transformation[direction[0]]
        elif cls.order == 2:
            raise NotImplementedError("")
        for at in metric_der.atoms(Function):
            local_at = type(cls)(at.args[0].subs(metric.general_function, cls.args[0]), at.args[1:])
            metric_der = metric_der.subs(at, local_at)
        return metric_der


class TemporalDerivative(Function, BasicDiscretisation):

    def __new__(cls, expr, *args):
        args = flatten([expr] + list(args))
        ret = super(TemporalDerivative, cls).__new__(cls, *args, evaluate=False)
        ret.store = True # By default all the derivatives are stored
        ret.local_evaluation = True
        return ret
    @property
    def simple_name(cls):
        return "%s"%("TD")
    @property
    def time_advance_array(cls):
        return cls.args[0]
    def classical_strong_differentiabilty_transformation(cls, metric):
        # No change to the class
        return cls

class OpenSBLIexpression(Equality, EinsteinStructure):

    def __new__(cls, expr):
        ret = super(OpenSBLIexpression, cls).__new__(cls, expr)
        return ret
    @property
    def simple_name(cls):
        return "%s"%("Expr")

class MetricDerivative(Function, BasicDiscretisation):
    """
    wrapper class to represent derivatives
    Sympy already have a "Derivative" class, thus double D
    """
    #nargs = (2,3,4,5,6,7)
    def __new__(cls, expr, *args):
        args = tuple(flatten([expr] + list(args)))
        ret = super(MetricDerivative, cls).__new__(cls, *args, evaluate=False)
        ret.store = True # By default all the derivatives are stored
        return ret

    def _discretise_derivative(cls, scheme):
        """This would return the descritised derivative of the
        local object depending on the order of accuracy specified
        Returns the formula for the derivative function, only first derivatives or homogeneous
        derivatives of higher order are supported. The mixed derivatives will be handled impl-
        citly while creating the kernels
        :arg derivative: the derivative on which descritisation should be performed
        :returns: the descritised derivative, in case of wall boundaries this is a Piecewise-
        function
        """
        order = cls.order
        form = 0
        # Put the coefficients of first and second derivatives in a dictionary and use them

        if cls.is_homogeneous:
            dire = cls.get_direction[0]
            weights = scheme._generate_weights(dire, order)
            for no, p in enumerate(scheme.points):
                expr = cls.args[0]
                for req in (cls.required_datasets):
                    loc = req.location[:]
                    loc[dire] = loc[dire] + p
                    #pprint([loc, req.location])
                    val = req.get_location_dataset(loc)
                    expr = expr.replace(req, val)
                form = form + weights[no]*expr
            if form == 0:
                raise ValueError("Central derivative formula is zero for %s"%cls)
        else:
            raise ValueError("")
        return form
    @property
    def simple_name(cls):
        return "%s"%("CD")


localfuncs = (MetricDerivative, KD, CentralDerivative, WenoDerivative, TemporalDerivative, LC, Dot)
simplifying_funcs = (KD, LC, Dot)
local_objects = ( DataObject, CoordinateObject, ConstantObject, EinsteinTerm)

import numpy as np
import operator
import math
import weakref
from pylab import imshow, show
from alge import Case, of, datatype
from collections import namedtuple
import time


UnaryOperation = datatype('UnaryOperation', ['operand', 'op', 'op_str'])
BinaryOperation = datatype('BinaryOperation', ['lhs', 'rhs', 'op', 'op_str'])
ArrayAssignOperation = datatype('ArrayAssignOperation', ['operand', 'key', 'value'])
ArrayNode = datatype('ArrayNode', ['data', 'owners'])
ArrayDataNode = datatype('ArrayDataNode', ['array_data'])
ScalarConstantNode = datatype('ScalarConstantNodeNode', ['value'])


def unary_op(op, op_str):

    def wrapper(func):
        def impl(self):
            return Array(data=UnaryOperation(self.array_node, op, op_str))

        return impl

    return wrapper


def binary_op(op, op_str):

    def wrapper(func):
        def impl(self, other):
            if isinstance(other, Array):
                other = other.array_node
            else:
                other = ScalarConstantNode(other)
            return Array(data=BinaryOperation(self.array_node, other, op, op_str))

        return impl

    return wrapper


class Array(object):

    def __init__(self, data=None):
        if isinstance(data, np.ndarray):
            data = ArrayDataNode(array_data=data)
        self._ref = weakref.ref(self)
        self.array_node = ArrayNode(data=data, owners=set([self._ref]))

    def __del__(self):
        self.array_node.owners.discard(self._ref)

    def get_data(self):
        if not isinstance(self.array_node.data, ArrayDataNode):
            data = Value(self.array_node)
            self.array_node.data = ArrayDataNode(data)
        return self.array_node.data.array_data

    def __str__(self):
        return str(self.get_data())

    def __repr__(self):
        return Repr(self.array_node, state={'level':0})

    @binary_op(operator.add, 'operator.add')
    def __add__(self, other):
        pass

    @binary_op(operator.sub, 'operator.sub')
    def __sub__(self, other):
        pass

    @binary_op(operator.mul, 'operator.mul')
    def __mul__(self, other):
        pass

    @binary_op(operator.div, 'operator.div')
    def __div__(self, other):
        pass

    @binary_op(operator.le, 'operator.le')
    def __le__(self, other):
        pass

    @binary_op(operator.pow, 'operator.pow')
    def __pow__(self, other):
        pass

    @binary_op(operator.getitem, 'operator.getitem')
    def __getitem__(self, other):
        pass

    def __setitem__(self, key, value):
        if isinstance(value, Array):
            value = value.array_node
        else:
            value = ScalarConstantNode(value)
        self.array_node = ArrayNode(data=ArrayAssignOperation(self.array_node, key, value),
                                    owners=set(self._ref))


@unary_op(abs, 'abs')
def numba_abs(operand):
    pass

@unary_op(math.log, 'math.log')
def numba_log(operand):
    pass

def sum(array):
    return np.sum(array.get_data())


class Value(Case):

    @of('ArrayNode(data, owners)')
    def array_node(self, data, owners):
        return Value(data)

    @of('ArrayDataNode(array_data)')
    def array_data_node(self, array_data):
        return array_data

    @of('ScalarConstantNode(value)')
    def scalar_constant(self, value):
        return value

    @of('UnaryOperation(operand, op, op_str)')
    def unary_operation(self, operand, op, op_str):
        return op(Value(operand))

    @of('BinaryOperation(lhs, rhs, op, op_str)')
    def binary_operation(self, lhs, rhs, op, op_str):
        return op(Value(lhs), Value(rhs))

    @of('ArrayAssignOperation(operand, key, value)')
    def array_assign_operation(self, operand, key, value):
        operator.setitem(Value(operand), key, Value(value))
        return Value(operand)


def get_indent(level):
    return ''.join([' '] * level * 4)

class Repr(Case):

    @of('ArrayNode(data, owners)')
    def array_node(self, data, owners):
        level = self.state['level']
        return '{0}ArrayNode (owned={1}): \n{2}'.format(get_indent(level),
            str(bool(owners)),
            str(Repr(data, state={'level':level+1})))

    @of('ArrayDataNode(array_data)')
    def array_data_node(self, array_data):
        level = self.state['level']
        return '{0}array_data: {1}\n'.format(get_indent(level), str(array_data))

    @of('ScalarConstantNode(value)')
    def scalar_constant(self, value):
        level = self.state['level']
        return '{0}value: {1}\n'.format(get_indent(level), str(value))

    @of('UnaryOperation(operand, op, op_str)')
    def unary_operation(self, operand, op, op_str):
        level = self.state['level']
        return '{0}UnaryOperation: \n{1}\n'.format(get_indent(level),
            Repr(operand, state={'level':level+1}))

    @of('BinaryOperation(lhs, rhs, op, op_str)')
    def binary_operation(self, lhs, rhs, op, op_str):
        level = self.state['level']
        return '{0}BinaryOperation: \n{1}\n{2}\n'.format(get_indent(level),
            Repr(lhs, state={'level':level+1}),
            Repr(rhs, state={'level':level+1}))

    @of('ArrayAssignOperation(operand, key, value)')
    def array_assign_operation(self, operand, key, value):
        level = self.state['level']
        return '{0}ArrayAssignOperation: \n{1}\n{2}\n'.format(get_indent(level),
            Repr(key, state={'level':level+1}),
            Repr(value, state={'level':level+1}))


class CodeGen(Case):

    @of('ArrayNode(data, owners)')
    def array(self, data, owners):
        return CodeGen(data, state=self.state)

    @of('ArrayDataNode(array_data)')
    def array_data_node(self, array_data):
        self.state['count'] += 1
        var_str = 'x' + str(id(array_data))
        if not var_str in self.state['inputs']:
            self.state['inputs'].append(var_str)
            self.state['input_types'].append(str(array_data.dtype))
        return var_str

    @of('ScalarConstantNode(value)')
    def scalar_constant(self, value):
        return str(value)

    @of('UnaryOperation(operand, op, op_str)')
    def unary_operation(self, operand, op, op_str):
        return op_str + '(' +  CodeGen(operand, state=self.state) + ')'

    @of('BinaryOperation(lhs, rhs, op, op_str)')
    def binary_operation(self, lhs, rhs, op, op_str):
        return op_str + '(' + CodeGen(lhs, state=self.state) + ',' + \
            CodeGen(rhs, state=self.state) + ')'


def test1():

    a1 = Array(data=np.arange(-10,10))
    a2 = Array(data=np.arange(-10,10))
    result = a1**2 + numba_abs(a2)

    print result.__repr__()
    print CodeGen(result.array_node, state={'count': 0})

    # Force
    print result

    print result.__repr__()
    print CodeGen(result.array_node, state={'count': 0})


def test2():

    a = Array(data=np.arange(100))
    b = Array(data=np.arange(100))

    c = a + b + a*2 + b*3

    print c.__repr__()

    inputs = []
    input_types = []
    body = CodeGen(c.array_node, state={'count':0, 'inputs':inputs, 'input_types':input_types})
    from numba import vectorize
    func = '''
def foo({0}):
    return {1}
'''.format(','.join(inputs), body)
    print func

    code = compile(func, '<string>', 'exec')

    exec(code, globals())

    foo = globals()['foo']

    ufunc = vectorize('(' + ','.join(input_types) + ')')(foo)

    t0 = time.time()
    for i in range(10000):
        ufunc(a.array_node.data.array_data, b.array_node.data.array_data)
    print time.time() - t0

    func = lambda x, y: x + y + x*2 + y*3
    t0 = time.time()
    for i in range(10000):
        func(a.array_node.data.array_data, b.array_node.data.array_data)
    print time.time() - t0

    print c.__repr__()


def test_mandelbrot():

    width = 900
    height = 600
    x_min = -2.0
    x_max = 1.0
    y_min = -1.0
    y_max = 1.0
    num_iterations = 20

    x, y = np.meshgrid(np.linspace(x_min, x_max, width),
                       np.linspace(y_min, y_max, height))

    c = Array(data = x + 1j*y)
    #z = c.copy()
    z = Array(data = x + 1j*y)

    image = Array(data = np.zeros((height, width)))

    for i in range(num_iterations):

        indices = (numba_abs(z) <= 10)
        z[indices] = (z[indices] ** 2) + c[indices]
        image[indices] = i

    imgplot = imshow(numba_log(image))
    show()


if __name__ == '__main__':
    test2()


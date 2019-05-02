#!/usr/bin/env python
# coding: utf-8
"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import Callable, Union, Set, Dict, Any, Tuple
from collections import namedtuple, OrderedDict, Counter
import multiprocessing as mp
from queue import Empty as EmptyQueueException
from yapyseq.common import YapyseqInternalError, evaluate_kwargs

# ------------------------------------------------------------------------------
# Custom types for this module
# ------------------------------------------------------------------------------

ExceptInfo = namedtuple("ExceptInfo", "function wrappers")
FunctionNodeResult = namedtuple("FunctionNodeResult", "nid exception returned")

# ------------------------------------------------------------------------------
# Custom exception for this module
# ------------------------------------------------------------------------------

class MultipleTransitionError(RuntimeError):
    pass


class NoTransitionError(RuntimeError):
    pass


class ConditionError(RuntimeError):
    pass


class ParallelSyncFailure(RuntimeError):
    pass


class PreviousNodeUndefined(ReferenceError):
    pass


class NodeFunctionTimeout(TimeoutError):
    pass


class NodeWrapperInitError(RuntimeError):
    """Raised when an error appears in the init of a wrapper."""
    def __init__(self, nid, wrapper_name, cause=None):
        """Initialize the exception.

        Args:
            nid: ID of the node where the exception occured.
            wrapper_name: (str) the name of the wrapper that raised the
                exception. Stored as a publict attribute of this object.
            cause: subclass on Exception. The exception raised by the wrapper
                that is the direct cause of this exception. Stored
                as a public attribute of this object.
        """
        self.nid = nid
        self.wrapper_name = wrapper_name
        self.cause = cause

    def __str__(self):
        msg = ("Wrapper '{}' of node '{}' raised the following exception "
               "during its initialization: \n\n{}").format(
                   self.wrapper_name, self.nid, self.cause)
        return msg


class NodeWrapperPreError(RuntimeError):
    """Raised when an error appears in the `pre` function of a wrapper."""
    def __init__(self, nid, wrapper_name, cause=None):
        """Initialize the exception.

        Args:
            nid: ID of the node where the exception occured.
            wrapper_name: (str) the name of the wrapper that raised the
                exception. Stored as a publict attribute of this object.
            cause: subclass on Exception. The exception raised by the wrapper
                that is the direct cause of this exception. Stored
                as a public attribute of this object.
        """
        self.nid = nid
        self.wrapper_name = wrapper_name
        self.cause = cause

    def __str__(self):
        msg = ("Wrapper '{}' of node '{}' raised the following exception "
               "during the run of 'pre' function: \n\n{}").format(
                   self.wrapper_name, self.nid, self.cause)
        return msg


class NodeWrapperPostError(RuntimeError):
    """Raised when an error appears in the `post` function of a wrapper."""
    def __init__(self, nid, wrapper_name, cause=None):
        """Initialize the exception.

        Args:
            nid: ID of the node where the exception occured.
            wrapper_name: (str) the name of the wrapper that raised the
                exception. Stored as a publict attribute of this object.
            cause: subclass on Exception. The exception raised by the wrapper
                that is the direct cause of this exception. Stored
                as a public attribute of this object.
        """
        self.nid = nid
        self.wrapper_name = wrapper_name
        self.cause = cause

    def __str__(self):
        msg = ("Wrapper '{}' of node '{}' raised the following exception "
               "during the run of 'post' function: \n\n{}").format(
                   self.wrapper_name, self.nid, self.cause)
        return msg

# ------------------------------------------------------------------------------
# Main classes
# ------------------------------------------------------------------------------

class Transition(object):
    """Class representing a transition."""

    def __init__(self, target: int, condition: str = None):
        """Initialize a Transition.

        Args:
            target: the nid of the targeted Node.
            condition: (optional) the condition to fulfill for this transition.
        """
        self._target = target
        self._condition = condition

    @property
    def target(self):
        return self._target

    def is_condition_fulfilled(self, variables: Dict):
        """Check if the condition is fulfilled with the given variables.

        Args:
            variables: a dictionary of variables that will be used to evaluate
              the condition.
        """
        # If there is no condition, it is considered as fulfilled
        if self._condition is None:
            return True

        # Evaluate the condition as a Python expression.
        # None is given as globals and variables are given as locals
        cond_res = eval(self._condition, None, variables)

        # If condition does not return a bool, raise an error
        if type(cond_res) is not bool:
            raise ConditionError("The following condition did not "
                                 "return a boolean : "
                                 "{}".format(self._condition))
        # Else, return the result
        else:
            return cond_res


class Node(object):
    """Class representing a Node.

    This class is not likely to be instantiated, as some children class describe
    the different types of nodes available in a sequence.
    """

    def __init__(self, nid: int, name: str = None):
        """Initialize a Node.

        Args:
            nid: the unique ID of the node.
            name: (optional) the name of the node.
        """
        self._nid = nid
        self._name = name
        self._previous_node_id = None

    @property
    def nid(self) -> int:
        """The unique ID of the node (read-only)."""
        return self._nid

    @property
    def name(self) -> str:
        """The name of the node. (read-only)

        Name is None if no name has been provided.
        """
        return self._name

    @property
    def previous_node_id(self):
        """The saved previous node id of this node.

        Raises:
            PreviousNodeUndefined: if no previous node is saved.
        """
        if self._previous_node_id:
            return self._previous_node_id
        else:
            raise PreviousNodeUndefined("Trying to get the previous node id"
                                        "but it is unknown...")

    @previous_node_id.setter
    def previous_node_id(self, value):
        self._previous_node_id = value


class WrappedNode(Node):
    """Class representing a node that contains wrappers."""

    def __init__(self, wrappers: OrderedDict, nid: int, name: str = None):
        """Initialize a WrapperManager.

        Args:
            wrappers: an OrderedDict of wrappers around this node.
                Keys are the names of wrapper classes, and values are arguments
                for constructors of these classes.
            nid: the unique ID of the node.
            name: (optional) the name of the node.
        """
        super().__init__(nid, name)
        self._wrappers_desc = wrappers if wrappers else OrderedDict()
        self._wrapper_objects = {}
        self._wrapper_classes = {}
        # Prepare a list of wrappers that run pre() successfully
        self._wrappers_pre_success = []

    @property
    def wrapper_names(self) -> Set[str]:
        """The set of wrapper names for this function (read-only)."""
        return set(self._wrappers_desc.keys())

    @property
    def wrapper_classes(self) -> Dict:
        """A dict. where keys are wrapper names and values are their classes."""
        return self._wrapper_classes

    @wrapper_classes.setter
    def wrapper_classes(self, given_dict: Dict):
        """Setter of wrapper_classes.

        Args:
            given_dict: dictionary where keys are wrapper names and values are
                their classes.

        Classes must inherit from yapyseq.NodeWrapper.
        """
        # Check that given dict contains all the required wrappers
        if not (Counter(given_dict.keys()) == Counter(self.wrapper_names)):
            raise YapyseqInternalError(
                ("Given wrapper classes does not match"
                 " saved wrapper names. Get {}, "
                 "expected {}").format(given_dict.keys(), self.wrapper_names))
        self._wrapper_classes = given_dict

    def _run_wrappers_pre(self, variables: Dict) -> None:
        """Initialize wrappers and run their 'pre' function.

        Args:
            variables: local variables taken into account while
                evaluating arguments of wrappers. It will be updated inside
                this function to add the sub-dictionnary 'wrappers'.
        Raises:
            * NodeWrapperPreError if one of the wrappers raised an exception.
              Original exception is set as a *cause* of this exception.
            * NodeWrapperInitError if one of the wrappers raised an exception
              while being instanciated. Original exception is set as a *cause*
              of this exception.
        """
        # Clean the previous dictionary
        self._wrapper_objects = {}
        # Initialize the wrapper dictionary inside variables
        variables['wrappers'] = {}
        # Iterate over all the wrappers
        for wrapper_name, wrapper_kwargs in self._wrappers_desc.items():
            # Initialize the wrapper
            try:
                # Make an instance of the wrapper, with its evaluated arguments
                evaluated_kwargs = evaluate_kwargs(wrapper_kwargs, variables)
                self._wrapper_objects[wrapper_name] = self._wrapper_classes[
                    wrapper_name](**evaluated_kwargs)
            except Exception as exc:
                raise NodeWrapperInitError(self.nid, wrapper_name, exc)
            # Run its `pre` function
            try:
                variables['wrappers'][wrapper_name] = self._wrapper_objects[
                    wrapper_name].pre()
            except Exception as exc:
                raise NodeWrapperPreError(self.nid, wrapper_name, exc)
            self._wrappers_pre_success.append(wrapper_name)

    def _run_wrappers_post(self) -> None:
        """Run the 'post' function of the wrappers.

        Raises:
            NodeWrapperPostError if one of the wrappers raised an exception.
            Original exception is set as a *cause* of this exception.
        """
        for wrapper_name, wrapper_obj in self._wrapper_objects.items():
            # Only run the post of wrappers that correctly did their pre
            if wrapper_name not in self._wrappers_pre_success:
                continue
            try:
                wrapper_obj.post()
            except Exception as exc:
                raise NodeWrapperPostError(self.nid, wrapper_name, exc)


class TransitionalNode(Node):
    """Class representing a node which contains outgoing transitions.

    This class is not likely to be instantiated, as some children class describe
    the different types of nodes available in a sequence.
    """

    def __init__(self, nid: int, transitions: Set, name: str = None):
        """Initialize a TransitionalNode.

        Args:
            nid: the unique ID of the node.
            transitions: the outgoing transitions of the node. Each item of the
              set must be a dictionary with the keys 'target' and 'condition',
              where 'target' contains the ID of the targeted node, and
              'condition', the Python expression to assess.
              'condition' is optional.
            name: (optional) the name of the node.
        """
        super().__init__(nid, name)
        self._transitions = set([
            Transition(t.get('target'), t.get('condition'))
            for t in transitions
        ])

    def get_all_next_node_ids(self) -> Set[int]:
        """Get the IDs of every nodes that can be reached from this one.

        It will return all the node IDs that are targeted by this current node,
        regardless the validity of the transitions. It can be seen as all the
        possible next nodes.

        Returns:
            A set of integers being the node ids of the possible next nodes.
        """
        return set([t.target for t in self._transitions])

    def get_next_node_id(self, variables: dict) -> Union[int, Set[int]]:
        """Return the ids of the next node to run in function of conditions.

        Transitions will be analyzed, using the given variables to assess
        their conditions, and winning transition(s) will lead to the next
        nodes(s).

        TODO: implement priorities among transitions
        TODO: implement the 'else' in conditions

        Args:
            variables: dictionary that contains all the variables that the
              conditions of the transitions might require. This dictionary will
              be added to the local variables before evaluating the condition
              expression.

        Returns:
            A set containing the IDs of all the next nodes to run next.

        Raises:
            NoTransitionError: if no transition is possible.
        """
        # This set will contain the conditions with a fulfilled condition
        winning_transitions = set()

        # For each candidate, check the condition
        for transition in self._transitions:
            if transition.is_condition_fulfilled(variables):
                winning_transitions.add(transition)

        # Create the set of target nodes, based on the winning transitions
        target_nodes = set(t.target for t in winning_transitions)

        # Check to raise NoTransitionError
        # A node MUST have at least one output transition.
        if len(target_nodes) == 0:
            raise NoTransitionError(("Node n°{} does not have any successful "
                                     "transition.").format(self.nid))

        return target_nodes


class SimpleTransitionalNode(TransitionalNode):
    """Class representing a node that can have only one transition target.

    This kind of node can have several transitions, but when they are evaluated
    to find the next node, only one transition can win.
    """

    def get_next_node_id(self, variables: dict):
        """Overriding of parent class.

        Raises:
            MultipleTransitionError: if several transitions are fulfilled at
              the same time, and therefore give several next nodes.
        """
        next_nodes = super().get_next_node_id(variables)
        if len(next_nodes) > 1:
            raise MultipleTransitionError(
                "Start node n°{} has several transition targets ({}) "
                "but it is forbidden.".format(self.nid, next_nodes))
        else:
            return next_nodes


class StartNode(SimpleTransitionalNode):
    """Class representing a node of type start."""
    pass


class StopNode(Node):
    """Class representing a node of type stop."""
    pass


class ParallelSplitNode(TransitionalNode):
    """Class representing a node of type 'parallel split'."""
    pass


class ParallelSyncNode(SimpleTransitionalNode):
    """Class representing a node of type 'parallel sync'."""

    def __init__(self, nid: int, transitions: Set, name: str = None):
        """Initialize a ParallelSyncNode.

        Args:
            nid: the unique ID of the node.
            transitions: the outgoing transitions of the node.
            name: (optional) the name of the node.
        """
        super().__init__(nid, transitions, name)
        # sync_history is the history of synchronization for a ParallelSyncNode.
        # It keeps track of the IDs of the previous nodes that led to this
        # synchronization node.
        self._sync_history = set()

        # the set of nodes that this ParallelSyncNode must synchronize.
        # It must set after initialization.
        self._nodes_to_sync = set()

    def set_nodes_to_sync(self, nids: Set[int]):
        """Set the list of nid to synchronize through this ParallelSyncNode.

        Args:
            nids: set containing the NIDs of the nodes that are targeting this
              ParallelSyncNode.
        """
        self._nodes_to_sync = nids

    def is_sync_initialized(self):
        """Check if the nodes to sync have been already declared."""
        return len(self._nodes_to_sync) > 0

    def is_sync_complete(self):
        """Check if the synchronization process of this node is complete."""
        if len(self._nodes_to_sync) == 0:
            raise ParallelSyncFailure(
                "Cannot check synchronization for node n°{}. "
                "Set of nodes to synchronize has not been "
                "initialized.".format(self.nid))
        if self._nodes_to_sync == self._sync_history:
            return True
        else:
            return False

    def clear_history(self):
        self._sync_history = set()

    def add_to_history(self, nid):
        self._sync_history.add(nid)


class FunctionNode(SimpleTransitionalNode, WrappedNode):
    """Class representing a node of type function."""

    def __init__(self,
                 nid: int,
                 function_name: str,
                 transitions: Set,
                 function_kwargs: Dict = None,
                 name: str = None,
                 timeout: int = None,
                 return_var_name: str = None,
                 wrappers: OrderedDict = None):
        """Initialize a FunctionNode.

        Args:
            nid: the unique ID of the node.
            function_name: the name of the function to run in the node.
            function_kwargs: (optional) the keyword arguments to give
              to the function.
            transitions: the outgoing transitions of the node.
            name: (optional) the name of the node.
            timeout: (optional) the timeout limit of the function, in seconds.
            return_var_name: (optional) the variable name in which the sequence
                runner will store the returned object of the function.
            wrappers: (optional) an OrderedDict of wrappers around this node.
                Keys are the names of wrapper classes, and values are arguments
                for constructors of these classes.
        """
        # Here I do NOT use super() because it becomes really hard to maintain
        # in case of inheritance diamond like here. Fore more information, read
        # https://fuhm.org/super-harmful/
        SimpleTransitionalNode.__init__(self, nid, transitions, name)
        WrappedNode.__init__(self, wrappers, nid, name)
        self._function_name = function_name
        self._function_kwargs = function_kwargs if function_kwargs else dict()
        self._timeout = timeout
        self._return_var_name = return_var_name

    @property
    def function_name(self) -> str:
        """The name of the function to run in the node (read-only)."""
        return self._function_name

    @property
    def return_var_name(self) -> str:
        """The variable name to store the returned object of the function."""
        return self._return_var_name

    @property
    def function_callable(self) -> Dict:
        """The callable of the function of this node."""
        return self._func_callable

    @function_callable.setter
    def function_callable(self, func_callable: Callable):
        """Setter of function_callable."""
        # Check that the name of the callable is the one expected
        if self._function_name != func_callable.__name__:
            raise YapyseqInternalError(
                ("Given callable has not the expected name. "
                 "Get {}, expected {}").format(
                     func_callable.__name__, self._function_name))
        self._func_callable = func_callable

    def _create_node_result(self, function_exception: Union[None, Exception],
                            wrappers_exception: Union[None, Exception],
                            returned_obj: Any) -> FunctionNodeResult:
        """Return an easy data structure containing result of a node.

        Args:
            exception: the exception object if the function raised one.
            returned_obj: the returned object if the function returned one.

        Returns:
            A namedtuple containing all the given data in a structured form.
        """
        # Add name to exception objects for more convenience
        if function_exception:
            function_exception.name = type(function_exception).__name__
        if wrappers_exception:
            wrappers_exception.name = type(wrappers_exception).__name__
        # Save exceptions in the result object
        if wrappers_exception or function_exception:
            except_info = ExceptInfo(function_exception, wrappers_exception)
        else:
            except_info = None
        # Create final result object
        res = FunctionNodeResult(self.nid, except_info, returned_obj)
        return res

    def _run_function_no_timeout(self,
                                 kwargs: Dict = None,
                                 queue: mp.Queue = None) -> Tuple:
        """Run the function without a timeout and return result.

        Property `function_callable` must be set before calling this method.

        Args:
            kwargs: (optional) The arguments to give to the function.
            queue: (optional) A queue to put the result, if given.
        Returns:
            2-tuple: returned_obj, raised_exception
            One of the items is necessary None.
        """
        # Run the callable
        try:
            func_res = self._func_callable(**kwargs)
        except Exception as exc:
            res = None, exc
        else:
            res = func_res, None
        if queue:
            queue.put(res)
        return res

    def _run_function_with_timeout(self, kwargs: Dict = None) -> Tuple:
        """Run the function with a timeout and return result.

        Property `function_callable` must be set before calling this method.

        Args:
            kwargs: (optional) The arguments to give to the function.

        Returns:
            2-tuple: returned_obj, raised_exception
            One of the items is necessary None.
        """
        # Create a sub-result queue for the real run of the function
        sub_result_queue = mp.Queue()
        # Start the function in the new sub-process
        process = mp.Process(target=self._run_function_no_timeout,
                             name="Node {} sub-process".format(self.nid),
                             kwargs={
                                 'queue': sub_result_queue,
                                 'kwargs': kwargs
                             })
        process.start()
        try:
            # Wait until result or timeout
            ret, exc = sub_result_queue.get(block=True, timeout=self._timeout)
        except EmptyQueueException:
            # timeout occurred !
            # Create a timeout exception to put in the result
            exc = NodeFunctionTimeout(
                "Function {} of node {} timed out !".format(
                    self.function_name, self.nid))
            return None, exc
        else:
            return ret, exc

    def run(self,
            result_queue: mp.Queue,
            variables: Dict) -> None:
        """Function that can be called in a subprocess to run a node function.

        Property `function_callable` must be set before calling this method.

        This function does:
          * Run wrappers of the node, with given arguments
          * Run the given callable that has been given, with the given arguments
          * Manage a Timeout on this callable if the node has one
          * Provide the result of the callable through a Queue

        Args:
            result_queue: The Queue object to store the result of the node
                function. The stored object will be of type FunctionNodeResult.
            variables: (optional) local variables taken into account while
                evaluating arguments of wrappers and function.
                Warning: this dict is modified by this function. Give a copy to
                avoid access conflict.
        """
        # Run wrappers pre
        pre_exc = None
        wrappers_failed = False
        try:
            self._run_wrappers_pre(variables)
        except (NodeWrapperInitError, NodeWrapperPreError) as exc:
            pre_exc = exc
            wrappers_failed = True

        # Run the function only if all of the wrappers succeeded
        if not wrappers_failed:
            # evaluate keyword arguments of the function
            try:
                evaluated_kwargs = evaluate_kwargs(self._function_kwargs, variables)
            except Exception as exc:
                # If evaluation failed, do not run the function and save the
                # exception as a function exception.
                func_ret, func_exc = None, exc
            else:
                if not self._timeout:
                    # Just start the function without timeout
                    # and without creating a new process.
                    # Note: this separate condition could be avoided because Queue.get
                    # manages a None timeout, but this implementation avoids creating
                    # unnecessary sub-processes, so it is better like this !
                    func_ret, func_exc = self._run_function_no_timeout(
                        evaluated_kwargs)
                else:
                    func_ret, func_exc = self._run_function_with_timeout(
                        evaluated_kwargs)
        # Function is not run and results are None
        else:
            func_ret, func_exc = None, None

        # Run wrappers post
        post_exc = None
        try:
            self._run_wrappers_post()
        except NodeWrapperPostError as exc:
            post_exc = exc

        # Create the final result object
        result = self._create_node_result(func_exc,
                                          pre_exc if pre_exc else post_exc,
                                          func_ret)
        # Provide result through the Queue
        result_queue.put(result)


class VariableNode(SimpleTransitionalNode):
    """Class representing a node of type variable."""

    def __init__(self,
                 nid: int,
                 variables: Dict,
                 transitions: Set,
                 name: str = None):
        """Initialize a VariableNode.

        Args:
            nid: the unique ID of the node.
            variables: a dictionary of variables and their assignations in
              the form of {var_name: python_expression}
            transitions: the outgoing transitions of the node.
            name: (optional) the name of the node.
        """
        super().__init__(nid, transitions, name)
        self._variables = variables

    @property
    def variables(self):
        """Dictionary of variables with python expressions as values."""
        return self._variables


# TODO: SequenceNode

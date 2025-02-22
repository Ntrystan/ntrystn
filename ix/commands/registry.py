import importlib
import inspect
from typing import Callable, Any

# Unique identifier for ix commands
IX_COMMAND_IDENTIFIER = "ix_command"


def get_function_signature(func):
    """
    Returns the signature of a function as a string, without the return type hint.
    """
    signature = inspect.signature(func)
    parameters = [
        f"{param.name}: {param.annotation.__name__ if hasattr(param.annotation, '__name__') else str(param.annotation)}"
        for param in signature.parameters.values()
    ]
    return ", ".join(parameters)


class Command:
    """A class representing a command.

    Attributes:
        name (str): The name of the command.
        description (str): A brief description of what the command does.
        signature (str): The signature of the function that the command executes. Defaults to None.
    """

    def __init__(
        self,
        name: str,
        description: str,
        method: Callable[..., Any],
        signature: str = None,
    ):
        self.name = name
        self.description = description
        self.method = method
        self.signature = signature if signature else get_function_signature(self.method)

    def __call__(self, *args, **kwargs) -> Any:
        return self.method(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.name}({self.signature})"


class CommandRegistry:
    """
    The CommandRegistry class is a manager for a collection of Command objects.
    It allows the registration, modification, and retrieval of Command objects,
    as well as the scanning and loading of command plugins from a specified
    directory.
    """

    def __init__(self):
        self.commands = {}

    def _import_module(self, module_name: str) -> Any:
        return importlib.import_module(module_name)

    def _reload_module(self, module: Any) -> Any:
        return importlib.reload(module)

    def register(self, cmd: Command) -> None:
        self.commands[cmd.name] = cmd

    def unregister(self, command_name: str):
        if command_name in self.commands:
            del self.commands[command_name]
        else:
            raise KeyError(f"Command '{command_name}' not found in registry.")

    def reload_commands(self) -> None:
        """Reloads all loaded command plugins."""
        for cmd_name in self.commands:
            cmd = self.commands[cmd_name]
            module = self._import_module(cmd.__module__)
            reloaded_module = self._reload_module(module)
            if hasattr(reloaded_module, "register"):
                reloaded_module.register(self)

    def get(self, name: str) -> Callable[..., Any]:
        return self.commands[name]

    def call(self, command_name: str, **kwargs) -> Any:
        if command_name not in self.commands:
            raise KeyError(f"Command '{command_name}' not found in registry.")
        command = self.commands[command_name]

        return command(**kwargs)

    def command_prompt(self) -> str:
        """
        Returns a string representation of all registered `Command` objects for use in a prompt
        """
        commands = list(self.commands.values())
        commands.sort(key=lambda cmd: cmd.name)
        return "\n".join(
            [f"{idx + 1}. {str(cmd)}" for idx, cmd in enumerate(commands)]
        )

    def import_commands(self, module_name: str) -> None:
        """
        Imports the specified Python module containing command plugins.

        This method imports the associated module and registers any functions or
        classes that are decorated with the `IX_COMMAND_IDENTIFIER` attribute
        as `Command` objects. The registered `Command` objects are then added to the
        `commands` dictionary of the `CommandRegistry` object.

        Args:
            module_name (str): The name of the module to import for command plugins.
        """

        module = importlib.import_module(module_name)

        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            # Register decorated functions
            if (
                hasattr(attr, IX_COMMAND_IDENTIFIER)
                and getattr(attr, IX_COMMAND_IDENTIFIER) is True
            ):
                self.register(attr.command)
            # Register command classes
            elif (
                inspect.isclass(attr) and issubclass(attr, Command) and attr != Command
            ):
                cmd_instance = attr()
                self.register(cmd_instance)

    @classmethod
    def for_tools(cls, tools: list) -> "CommandRegistry":
        """Loads a CommandRegistry instance with the specified tools."""
        # load instance specific tools
        tool_registry = cls()
        for class_path in tools or []:
            tool_registry.import_commands(class_path)
        return tool_registry


def command(name: str, description: str, signature: str = None) -> Callable[..., Any]:
    """The command decorator is used to create Command objects from ordinary functions."""

    def decorator(func: Callable[..., Any]) -> Command:
        cmd = Command(
            name=name, description=description, method=func, signature=signature
        )

        def wrapper(*args, **kwargs) -> Any:
            return func(*args, **kwargs)

        wrapper.command = cmd

        setattr(wrapper, IX_COMMAND_IDENTIFIER, True)
        return wrapper

    return decorator

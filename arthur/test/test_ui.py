import urwid

from arthur import ui
from arthur.test.fakes import FakeWorkbench
from twisted.trial.unittest import SynchronousTestCase
from zope.interface import implementer, verify


class ConstantsTests(SynchronousTestCase):
    def test_palette(self):
        """
        The palette contains header, foreground and background attributes.
        """
        expected = {
            "header": ("black", "dark green"),
            "foreground": ("dark green", "black"),
            "background": ("dark gray", "black"),
            "alert": ("yellow" , "dark red")
        }
        for attributeTuple in ui.DEFAULT_PALETTE:
            name, attrs = attributeTuple[0], attributeTuple[1:]
            self.assertEqual(expected[name], attrs)


    def test_background(self):
        """
        The background is a solid fill with the right display attribute.
        """
        self.assertEqual(ui.BACKGROUND.attr_map, {None: "background"})

        widget = ui.BACKGROUND.original_widget
        self.assertTrue(isinstance(widget, urwid.SolidFill))
        self.assertEqual(widget.fill_char, u"\N{LIGHT SHADE}")


    def test_divider(self):
        """
        The divider consists of an upper one eight block with no padding.
        """
        self.assertEqual(ui.DIVIDER.div_char, u"\N{UPPER ONE EIGHTH BLOCK}")
        self.assertEqual(ui.DIVIDER.top, 0)
        self.assertEqual(ui.DIVIDER.bottom, 0)



class WorkbenchTests(SynchronousTestCase):
    """
    Tests for the workbench.
    """
    def setUp(self):
        self.workbench = ui.Workbench()


    def test_background(self):
        """
        The empty workbench's widget's body consists of a background.
        """
        body, _options = self.workbench.widget.contents["body"]
        self.assertIdentical(body, ui.BACKGROUND)


    def test_header(self):
        """
        The empty workbench has a header.

        This checks the type of the ``header`` attribute, and verifies
        that the header attribute's widget is used.
        """
        self.assertTrue(isinstance(self.workbench.header, ui.Header))
        widget, _options = self.workbench.widget.contents["header"]
        self.assertIdentical(self.workbench.header.widget, widget)


    def assertDisplayed(self, tools):
        """
        The given tools are displayed from top to bottom, and that the
        title is that of the top tool or empty if there are no tools.
        """
        expectedTitle = u"" if not tools else tools[0].name
        self.assertEqual(self.workbench.header.title.text, expectedTitle)

        layer, _options = self.workbench.widget.contents["body"]
        for tool in tools:
            self.assertEqual(layer.attr_map, {None: "foreground"})
            overlay = layer.original_widget
            self.assertIdentical(overlay.top_w, tool.widget)
            layer = overlay.bottom_w

        self.assertIdentical(layer, ui.BACKGROUND)


    def test_display(self):
        """
        The workbench displays tools.
        """
        tool = DummyTool(u"Tool")
        self.workbench.display(tool)
        self.assertDisplayed([tool])


    def test_nestedDisplay(self):
        """
        The workbench displays multiple overlapping tools.
        """
        first = DummyTool(u"First")
        self.workbench.display(first)
        second = DummyTool(u"Second")
        self.workbench.display(second)
        self.assertDisplayed([second, first])


    def test_clear(self):
        """
        Clearing the display removes existing tools.

        When tools are later added again, the old tools are gone.
        """
        first = DummyTool(u"First")
        self.workbench.display(first)
        second = DummyTool(u"Second")
        self.workbench.display(second)

        self.workbench.clear()
        self.assertDisplayed([])
        self.assertEqual(self.workbench.header.title.text, u"")

        third = DummyTool(u"Third")
        self.workbench.display(third)
        self.assertDisplayed([third])



@implementer(ui.ITool)
class DummyTool(object):
    """
    A dummy tool, with a name, widget and position.
    """
    def __init__(self, name):
        self.name = name
        self.widget = DummyWidget()
        self.position = "center", 1, "middle", 1



class DummyWidget(object):
    """
    A dummy widget.
    """



class HeaderTests(SynchronousTestCase):
    """
    Tests for the workbench header.
    """
    def setUp(self):
        self.header = ui.Header()


    def test_title(self):
        """
        The header has a title which is empty and left-aligned.
        """
        title = self.header.title
        self.assertEqual(title.text, u"")
        self.assertEqual(title.align, "left")


    def test_aside(self):
        """
        The header has an aside which is empty and right-aligned.
        """
        aside = self.header.aside
        self.assertEqual(aside.align, "right")
        self.assertIn(u"C-w to quit", aside.text)


    def test_widget(self):
        """
        The header widget consists of the title and the aside, arranged as
        columns, and renders them with the ``header`` display attribute.
        """
        self.assertEqual(self.header.widget.attr_map, {None: "header"})
        contents = self.header.widget.original_widget.contents
        widgets = [widget for widget, _options in contents]
        self.assertEqual(widgets, [self.header.title, self.header.aside])



class LauncherTests(SynchronousTestCase):
    def setUp(self):
        self.workbench = FakeWorkbench()
        self.tools = map(DummyTool, u"abcd")
        self.launcher = ui.Launcher(self.workbench, self.tools)


    def test_interface(self):
        """
        The launcher implements the ``ITool`` interface.
        """
        verify.verifyObject(ui.ITool, self.launcher)


    def test_menu(self):
        """
        The menu has a title, divider and a button for each tool.

        The buttons are labeled with the tool names. When clicked, the
        buttons launch the tools.
        """
        elements = iter(self.launcher.menu.body)

        self.assertEqual(next(elements).text, u"Select a tool to launch")
        self.assertIdentical(next(elements), ui.DIVIDER)

        for mapped, tool in zip(elements, self.tools):
            self.assertEqual(mapped.attr_map, {None: "foreground"})
            self.assertEqual(mapped.focus_map, {None: "header"})

            button = mapped.original_widget
            self.assertEqual(button.label, tool.name)

            button.keypress((1,), "enter")
            self.assertEqual(self.workbench.tools, [tool])
            self.workbench.clear()



class UnhandledInputTests(SynchronousTestCase):
    def test_quit(self):
        """The unhandled input handler raises urwid.ExitMainLoop on C-w.

        """
        self.assertRaises(urwid.ExitMainLoop,
                          ui._unhandledInput, "ctrl w",
                          workbench=None, launcher=None)


    def test_clear(self):
        """When escape is pressed, the workbench shows just the launcher.

        """
        workbench = FakeWorkbench()
        launcher = object()
        workbench.display(launcher)
        self.assertNotEqual(workbench.tools, [])

        self.assertTrue(ui._unhandledInput("esc",
                                         workbench=workbench,
                                         launcher=launcher))
        self.assertEqual(workbench.tools, [launcher])


    def test_other(self):
        """The unhandled input handler returns a falsey value for an unhandled
        event.

        """
        self.assertFalse(ui._unhandledInput(
            "xyzzy", workbench=None, launcher=None))



class NotificationTests(SynchronousTestCase):
    """Tests for pop-up notifications.

    """
    def test_interface(self):
        """The notification class implements the tool interface.

        """
        notification = ui._Notification(u"name", u"text")
        verify.verifyObject(ui.ITool, notification)


    def test_notify(self):
        """The notify convenience function displays a notification. When it
        is dismissed, the returned deferred fires.

        """
        workbench = FakeWorkbench()
        d = ui.notify(workbench, u"name", u"notification text")

        tool, = workbench.tools
        self.assertEqual(tool.name, u"name")

        self.assertEqual(tool.textWidget.text, u"notification text")

        urwid.emit_signal(tool.button, "click")

        self.assertEqual(self.successResultOf(d), None)
        self.assertEqual(workbench.tools, [])



class PromptTests(SynchronousTestCase):
    def test_interface(self):
        """The prompt class implements the tool interface.

        """
        prompt = ui._Prompt(u"name", u"prompt")
        verify.verifyObject(ui.ITool, prompt)


    def test_prompt(self):
        """The prompt convenience function displays a prompt. When the prompt
        is completed, the result is provided in the given deferred.

        """
        workbench = FakeWorkbench()
        d = ui.prompt(workbench, u"name", u"prompt text")

        tool, = workbench.tools
        self.assertEqual(tool.name, u"name")

        edit = tool.prompt
        editText, _attrs = edit.get_text()
        self.assertEqual(editText, u"prompt text")

        edit.insert_text(u"entered value")

        urwid.emit_signal(tool.button, "click")

        self.assertEqual(self.successResultOf(d), u"entered value")
        self.assertEqual(workbench.tools, [])

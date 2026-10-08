# Auto Layout Basics
*Class: Intro to Figma (example) · Section 3: Layout*

## Vocabulary
- **Auto layout**: a set of rules you give a frame so the items inside arrange themselves, "like a little stack." When content changes, the frame resizes automatically.
- **Direction**: whether auto layout stacks items vertically (down arrow) or horizontally (right arrow).
- **Gap**: the space between each item inside an auto layout frame.
- **Padding**: the space between the edge of the frame and its content. Can be set for all sides at once or per side.
- **Fixed width/height**: the frame stays exactly the size you set, whatever is inside.
- **Hug contents**: the frame shrinks or grows to wrap tightly around its contents.
- **Fill container**: the frame stretches to fill the space its parent frame gives it.
- **Flexbox**: the CSS layout system that auto layout closely resembles. *(Not defined in this lecture.)*

## Main Concepts

### Auto layout makes designs resize themselves
Instead of positioning things by hand, you describe the rules: direction, spacing, padding. Change the content (e.g. a longer button label) and everything adjusts. The instructor calls it the feature that changed how they design in Figma more than anything else.

### The three resizing modes
Width and height each have three settings, and this is the part that "confuses everybody":
- **Fixed**: never changes size.
- **Hug contents**: wraps the content. Right for buttons, so the button grows with its label.
- **Fill container**: stretches to the parent. E.g. a button set to fill container inside a card spans the full card width.

### Nesting builds real layouts
Auto layout frames can sit inside each other: a vertical card containing a horizontal row of buttons. Building this way produces layouts that behave like real web pages and map closely to CSS flexbox, which makes handoff to developers easier.

## How-to Steps

### Turn a text layer into an auto layout button
1. Select the text layer (e.g. "Sign up").
2. Press **Shift + A** to wrap it in an auto layout frame.
3. In the right-hand panel's **Auto layout** section, set **Direction** to horizontal.
4. Set the **Gap** (e.g. 8).
5. Set **Padding** per side using the individual-sides icon: 12 top/bottom, 24 left/right.
6. Set width and height to **Hug contents**.

## Shortcuts, Settings & Code
| Action | How |
|---|---|
| Add auto layout | `Shift + A` |
| Set padding per side | Click the individual-sides icon next to padding |

## Tips & Gotchas
- ⚠️ If your auto layout "isn't doing anything", check the resizing settings first. Everything set to Fixed is the cause "nine times out of ten."
- 💡 Buttons look better with more horizontal padding than vertical padding.
- 💡 Nest auto layout frames to build layouts that behave like real web pages. Developers will thank you.

## Resources Mentioned
- **Figma Help Center** article on auto layout (the instructor links it in the lecture's resources).

## Key Takeaways
- Auto layout = rules (direction, gap, padding) that let frames arrange and resize themselves.
- Use **Hug contents** for buttons, **Fill container** to stretch to a parent, and **Fixed** only when size must never change.
- Broken auto layout is almost always a resizing setting.
- Nesting auto layouts mirrors CSS flexbox, which makes developer handoff easier.

## Review Questions
1. What's the difference between Hug contents and Fill container?
   <details><summary>Answer</summary>Hug contents wraps tightly around the frame's contents; Fill container stretches to the space the parent frame provides.</details>
2. Your auto layout frame doesn't resize when you edit its text. What should you check first?
   <details><summary>Answer</summary>The resizing settings. It's probably set to Fixed instead of Hug contents.</details>
3. Which resizing mode should a button use, and why?
   <details><summary>Answer</summary>Hug contents, so the button grows or shrinks when its label changes.</details>
4. Why does nesting auto layout frames help developers?
   <details><summary>Answer</summary>Nested auto layouts behave like real web layouts and map closely to CSS flexbox.</details>

**Next up:** Turning this button into a reusable component.

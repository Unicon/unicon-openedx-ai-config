# [ARCH] Document all acceptable/valid competency criteria combinations that need to be displayed.

GitHub: https://github.com/openedx/openedx-core/issues/731 (#731, OPEN)
Cached: 2026-09-21

Given that people have the option to configure a set wide variety of Competency Criteria in the UI via these designs:

<img width="3548" height="2574" alt="Image" src="https://github.com/user-attachments/assets/3b109423-0342-419b-ac31-194150874546" />

<img width="3548" height="2574" alt="Image" src="https://github.com/user-attachments/assets/40bcd2a3-d3f8-4335-9b98-f1c39ee45ebc" />

<img width="3548" height="2574" alt="Image" src="https://github.com/user-attachments/assets/c03af0f3-6458-4e28-9765-8383dcab321b" />

And that our possible pilot partners have the following use cases:
<details>
<summary>Education Design Lab Scenario</summary>
EDL has 1 course per competency, with each course consisting of 4 sub-competencies. Each sub-competency is assessed via a single LTI assessment that produces a large number of lineitems, which I forget what they're called, but let's think of them as sub-sub-competencies, which should each appear as their own subsection in the platform. EDL would come to the Competency management page and click on a sub-competency and then find the course for the corresponding competency and then find the corresponding 4-6 sub-sub-competency assignments. If the learner earns 75% or higher on ALL of those sub-sub-competency assignments, then they have demonstrated mastery of the sub-comptency. If a learner does not demonstrate mastery of any one of the sub-competencies in the course after attempting it, then they are given the option to take a Capstone LTI assessment, which may be in the same course or may be in a different course depending on how the LMS was able to configure it. This Capstone LTI Assessment tests all 4 sub-comptencies at the same time so it produces something on the order of 20-24 lineitems which would each appear as their own subsection in the LMS. Some of those lineitems will correspond to the sub-competency. So the learner also has the option to demonstrate mastery of the sub-comptency by earning 75% or higher on ALL of the Capstone sub-sub-comptency lineitems that are in this course or in a separate course.

EDL Example:
Competency: Initiative
Sub-competencies and their lineitems/subsections:
- Lead Without Title
    1. Takes ownership for tasks that need to be completed in a given situation.
    2. Clearly and persuasively expresses an issue and need for action.
    3. Evaluates and takes action to manage team morale. 
    4. Vocalizes thoughts and actively contributes to team outcomes.
- Demonstrate Self-Awareness
    1. Accurately identifies own strengths and limitations
    2. Reflects on how personal beliefs may impact interactions with others
    3. Uses awareness of past actions to inform future actions 
    4. Recognizes personal motivations and biases
    5. Can identify and manage emotions in a variety of contexts
- Act as a Catalyst
    1. Galvanizes others to action
    2. Identifies and acts on opportunities for change
    3. Overcomes organizational inertia
- Learn From Experience
    1. Welcomes and applies feedback
    2. Reflects on situations with a growth mindset
    3. Identifies failure as an opportunity for greater understanding
    4. Consciously challenges negative self-talk

Initiative Capstone Lineitems/Subsections:
- Lead Without Title
    1. Takes ownership for tasks that need to be completed in a given situation.
    2. Clearly and persuasively expresses an issue and need for action.
    3. Evaluates and takes action to manage team morale.
- Demonstrate Self-Awareness
    1. Accurately identifies own strengths and limitations
    2. Uses awareness of past actions to inform future actions 
    3. Recognizes personal motivations and biases
    4. Can identify and manage emotions in a variety of contexts
- Act as a Catalyst
    1. Galvanizes others to action
    2. Identifies and acts on opportunities for change
- Learn From Experience
    1. Welcomes and applies feedback
    2. Identifies failure as an opportunity for greater understanding
    3. Consciously challenges negative self-talk
</details>

<details>
<summary> Calbright Free Durable Skills Courses Scenario</summary>
Calbright has each course correspond to a single competency which has 3 sub-competencies. Each sub-competency has its own formative assessment that would correspond to a subsection assignment in Open edX. Each course also has a Summative assessment that covers all 3 of the sub-competencies at once, which would also correspond to a single subsection in Open edX. So When they get to the competency management page, they would pick one of their subcompetencies on the left and then on the right, find the course and select that the learner must earn 75% or higher on both the formative subsection for that sub-competency and the summative subsection in that course.

Calbright Example:
Competency: Oral Communication
Sub-competencies:
- Dialogue
- Organized Speaking
- Persuasive Oral Communication
</details>

Document all of the scenarios that need to be supported by the Student Progress page's "COMPLETE ALL OF THE FOLLOWING AT 80% OR BETTER" display:

<img width="1090" height="639" alt="Image" src="https://github.com/user-attachments/assets/d82c24c0-96ed-4849-ac6a-21a779dc8200" />

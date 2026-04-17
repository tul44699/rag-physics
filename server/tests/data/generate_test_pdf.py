"""Generate a small test PDF with known physics content using fpdf2."""

from pathlib import Path

from fpdf import FPDF

OUTPUT_PATH = Path(__file__).parent / "test_physics.pdf"

PAGES = [
    # Page 1: Newton's First Law
    (
        "Newton's First Law of Motion states that an object at rest stays at rest "
        "and an object in motion stays in motion with the same speed and in the same "
        "direction unless acted upon by an unbalanced force. This is the law of inertia. "
        "Force is not required to maintain motion, but rather to change it. Galileo first "
        "formulated this principle through his experiments with inclined planes. "
        "The concept of inertia explains why passengers lurch forward when a car stops suddenly. "
        "Inertial reference frames are those in which Newton's first law holds true. "
    ) * 3,
    # Page 2: Newton's Second Law
    (
        "Newton's Second Law establishes the quantitative relationship between force, mass, "
        "and acceleration: F equals m a. The net force acting on an object equals the product of "
        "its mass and acceleration. This vector equation means acceleration is in the "
        "same direction as the net force. The SI unit of force is the newton, defined as "
        "kilogram meters per second squared. This law allows prediction of motion given forces. "
        "Free-body diagrams help visualize all forces acting on an object. "
    ) * 3,
    # Page 3: Newton's Third Law
    (
        "Newton's Third Law states that for every action, there is an equal and opposite "
        "reaction. When object A exerts a force on object B, object B simultaneously exerts "
        "a force of equal magnitude but opposite direction on object A. These forces act on "
        "different objects, so they do not cancel. Examples include the recoil of a gun, "
        "the propulsion of a rocket, and the normal force between surfaces in contact. "
        "Action-reaction pairs are fundamental to understanding interactions. "
    ) * 3,
    # Page 4: Conservation of Energy
    (
        "The law of Conservation of Energy states that energy cannot be created or destroyed, "
        "only transformed from one form to another. The total energy of an isolated system "
        "remains constant. In mechanical systems, energy transforms between kinetic energy "
        "and potential energy. Kinetic energy equals one-half m v squared, and gravitational "
        "potential energy equals m g h. Non-conservative forces like friction "
        "convert mechanical energy into thermal energy. The work-energy theorem relates "
        "net work to the change in kinetic energy. "
    ) * 3,
    # Page 5: Conservation of Momentum
    (
        "Conservation of Momentum states that the total momentum of a closed system remains "
        "constant in the absence of external forces. Momentum p equals m v is a vector quantity. "
        "In collisions, total momentum before equals total momentum after. Elastic collisions "
        "conserve both momentum and kinetic energy, while inelastic collisions conserve only "
        "momentum. The impulse-momentum theorem relates impulse J equals F delta t to "
        "the change in momentum delta p. Center of mass motion is unaffected by internal forces. "
    ) * 3,
]


def generate():
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    for page_text in PAGES:
        pdf.add_page()
        pdf.set_font("Helvetica", size=11)
        pdf.multi_cell(0, 5, page_text)
    pdf.output(str(OUTPUT_PATH))
    return OUTPUT_PATH


if __name__ == "__main__":
    path = generate()
    print(f"Generated test PDF: {path} ({path.stat().st_size} bytes)")

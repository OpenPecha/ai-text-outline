"""Shared test fixtures and utilities."""

import pytest


@pytest.fixture
def sample_tibetan_text():
    """Sample Tibetan text with ToC section for testing."""
    return """༄༅། །གཞུང་ལུགས་རལ་བ་

དཀར་ཆག
རིས་པ་གཉིས་པ་དྲི་མ་མེད་པའི་འོད། …………………………(1)
དཔལ་རྡོ་རྗེ་འཇིགས་བྱེད་ཀྱི་ཞི་རྒྱས་ཀྱི་སྦྱིན་སྲེག (170)
དཔལ་རྡོ་རྗེ་འཇིགས་བྱེད་ལྷ་བཅུ་གསུམ་མའི་བསྐྱེད། (186)
ས་ལམ་གྱི་རྣམ་གཞག་མཁས་པའི་ཡིད་འཕྲོག ……(249)

དཀར་ཆག

[1] First Section Content Here
Lorem ipsum dolor sit amet
[170] Second Section
More content
[186] Third Section
Even more content
[249] Fourth Section
Final content
"""


@pytest.fixture
def sample_toc_dict():
    """Expected ToC dictionary for sample text."""
    return {
        "རིས་པ་གཉིས་པ་དྲི་མ་མེད་པའི་འོད།": 1,
        "དཔལ་རྡོ་རྗེ་འཇིགས་བྱེད་ཀྱི་ཞི་རྒྱས་ཀྱི་སྦྱིན་སྲེག": 170,
        "དཔལ་རྡོ་རྗེ་འཇིགས་བྱེད་ལྷ་བཅུ་གསུམ་མའི་བསྐྱེད།": 186,
        "ས་ལམ་གྱི་རྣམ་གཞག་མཁས་པའི་ཡིད་འཕྲོག": 249,
    }

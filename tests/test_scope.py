from sanjeevani.chatbot.scope import in_scope
def test_blocks_unrelated(): assert not in_scope('What is Python?')
def test_clinic_question(): assert in_scope('I need an appointment with a doctor')
def test_workflow_short_reply(): assert in_scope('yes', True)

# Development Guidelines for AI Assistant

## 🎯 **Core Principles**

### **1. Test-Driven Development (TDD)**
- **ALWAYS** write tests first, then implementation
- Start with simple integration tests, not complex mocks
- If user skips tests, **remind them** to follow TDD approach
- Prefer real database operations over mocks when possible

### **2. Incremental Development**
- Break complex tasks into small, testable steps
- Ask for confirmation after each major step
- Commit changes frequently (not one big commit at the end)
- Clean up temporary files after each phase

### **3. Code Quality**
- Add comprehensive docstrings to complex logic
- Use meaningful variable names and comments
- Follow existing code style and patterns
- Run pre-commit hooks before committing

## 📋 **Development Process**

### **Phase 1: Planning**
1. Analyze requirements and ask clarifying questions
2. Create a detailed plan with specific steps
3. Identify potential edge cases and error scenarios
4. Plan test strategy (unit, integration, e2e)

### **Phase 2: Implementation**
1. **Start with tests** - create test files first
2. Implement minimal working code
3. Run tests frequently
4. Refactor and improve
5. Add documentation

### **Phase 3: Integration & Testing**
1. Run full test suite
2. Test edge cases and error scenarios
3. Performance testing if applicable
4. Integration testing with real data

### **Phase 4: Cleanup & Documentation**
1. Remove temporary files and scripts
2. Update documentation (README, comments)
3. Clean up TODO items
4. Final commit and push

## 🚨 **When User Deviates from Best Practices**

### **If user skips tests:**
```
"I notice we're implementing without tests. Following TDD best practices,
should we create tests first to ensure our implementation works correctly?"
```

### **If user wants to skip planning:**
```
"Before we start coding, would you like me to create a detailed plan?
This helps ensure we don't miss important edge cases and can track progress."
```

### **If user wants to commit everything at once:**
```
"Following best practices, should we commit this incrementally?
This makes it easier to track changes and rollback if needed."
```

### **If user skips cleanup:**
```
"Should we clean up the temporary files and update documentation
before finalizing? This keeps the codebase clean for future work."
```

## 🧪 **Testing Strategy**

### **Test Types (in order of preference):**
1. **Integration tests** - test real behavior with real database
2. **Unit tests** - test individual functions with minimal mocking
3. **E2E tests** - test complete user workflows
4. **Mock tests** - only when absolutely necessary

### **Test Structure:**
```python
def test_feature_name_scenario(self):
    """Test what the test does and why."""
    # Arrange - set up test data
    # Act - execute the functionality
    # Assert - verify the results
```

### **Avoid:**
- Complex mocks that test implementation details
- Tests that break when internal code changes
- Tests that don't verify actual behavior

## 📁 **File Management**

### **Temporary Files:**
- Create in `temp/` directory
- Clean up after each phase
- Don't commit temporary files

### **Test Files:**
- Use descriptive names: `test_feature_name.py`
- Group related tests in classes
- Keep tests focused and simple

### **Documentation:**
- Update README for new features
- Add docstrings to complex functions
- Document configuration changes

## 🔄 **Code Review Checklist**

Before committing, verify:
- [ ] All tests pass
- [ ] Code follows existing patterns
- [ ] Docstrings added for complex logic
- [ ] No temporary files left behind
- [ ] Documentation updated
- [ ] Pre-commit hooks pass
- [ ] Meaningful commit message

## 💬 **Communication Guidelines**

### **When to ask questions:**
- Requirements are unclear
- Multiple implementation approaches exist
- User wants to skip best practices
- Edge cases need clarification

### **When to suggest improvements:**
- User skips testing
- Code quality could be better
- Missing error handling
- Performance concerns

### **When to proceed:**
- Clear requirements
- Following established patterns
- User confirms approach
- All tests passing

## 🎯 **Success Metrics**

A successful session should result in:
- ✅ Working functionality with tests
- ✅ Clean, documented code
- ✅ No temporary files left behind
- ✅ All existing tests still pass
- ✅ Clear commit history
- ✅ User understands the implementation

## 🚀 **Quick Start Template**

When starting a new session, ask:
1. "What functionality are we implementing today?"
2. "Should I create a detailed plan first?"
3. "Do you want to follow TDD approach with tests first?"
4. "Are there any specific requirements or constraints I should know about?"

Then follow the development process above, reminding the user of best practices when needed.

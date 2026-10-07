# Testing Guidelines (Vitest)

The team's source guidelines, kept deliberately as the statement of intent. SKILL.md
and `Web/test/README.md` are the operational form and overlap with it on purpose; when
in doubt about intent, this document is the authority.

## Core philosophy

- **Tests are documentation.** The *arrange* and *act* sections should demonstrate
  how the software is intended to be used; the *assert* section verifies the results
  we'd expect.
- **Use real objects, not fake data.** When a function requires an object, construct
  the real thing.
- **Keep these as unit tests.** If something requires mocks, it's really an
  integration test — don't put it here.

## Structure — follow Arrange / Act / Assert

```js
// arrange

// act

// assert
```

## What to cover

- Private functions, including private helper functions.
  - Cover private helpers through the public export that calls them; if logic is
    unreachable that way, it is out of scope — we do not restructure production
    code to enable testing.
- Variable state.
- Intended usage — the happy path.
- Misuse — the unhappy path.
- Orchestrating functions (the ones that coordinate other functions).

## Test matrices

- Use test matrices to cover combinations of inputs/states.
- Where possible, express the matrix state as a function with a descriptive name,
  so the intent of what the function is aiming for is visible at a glance.

## Organization

- Organize tests so it's immediately clear which component each one is testing.

## Critical review

- We want to make sure we don't write the test for the implementation —
  we write the tests for the intended implementation.
- Tests are there to plan intended behavior.
- Tests are worth nothing if they don't fail when they should fail.
- There are scenarios where we can expect a test to fail, but this should not
  be a first step — it's something we can discuss based on the failing tests.
  Adding expected-failure markers early can open up for hiding unintended
  failures.
- We are not interested in framework or language features. But we should test
  whether a function can take the number size of the intended design — we are
  not testing whether an int can take its max, but whether the function
  supports what was planned.

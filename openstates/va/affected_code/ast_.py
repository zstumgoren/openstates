from tater.node import Node, matches, matches_subtypes
from tater.tokentype import Token
from tater.common import HasSubdivisions


t = Token


class Start(Node):
    @matches(t.Type)
    def handle_bill(self, *items):
        return self.ascend(Bill, items, related=False)


class Bill(Node):

    @matches_subtypes(t.Amend)
    def amend(self, *items):
        return self.descend(Amend, items)


class Source(Node):
    # @matches(t.Division)
    # def handle_division(self, *items):
    #     return self.descend(Division, items)

    @matches(t.Semicolon)
    def handle_sem(self, *items):
        'We hit the end of an impact clause.'
        return self.pop()


class SessionLaw(Node):
    pass


class Enumeration(HasSubdivisions):
    @matches(t.Enumeration)
    def handle_enumeration(self, *items):
        'Add it as a sibling.'
        return self.parent.append(Enumeration(*items))

    @matches(t.A, t.Division, t.Numbered)
    def handle_division_numbered(self, *items):
        _, div, _ = items
        return self.descend(Division, div)

    @matches(t.Of, t.Division, t.Enumeration)
    def handle_division_of(self, *items):
        '''Insert this division and enumeration above this
        enumeration and its parent division.'''
        _, div, enum = items
        enum = self.parent.swap(Enumeration, enum)
        div = enum.swap(Division, div)
        # And resume where we left off.
        return self


class Division(Node):

    @matches(t.And)
    def skip_and(self, *items):
        '''Skip 'and' in lists of citations.
        '''
        return self

    @matches(t.Enumeration)
    def handle_enumeration(self, *items):
        'Add a child.'
        return self.descend(Enumeration, items)

    @matches(t.Numbered)
    def skip_numbered(self, *items):
        '''adding sections numbered 11-16.1'''
        return self


class Change(Node):

    @matches(t.And)
    def skip_and(self, *items):
        '''Skip 'and' in lists of citations.
        '''
        return self

    @matches(t.Division)
    def handle_division(self, *items):
        return self.descend(Division, items)

    @matches(t.In, t.Division)
    def handle_division_in(self, *items):
        '''to amend the Code of Virginia by adding in
        Title 59.1 a chapter numbered 50, consisting...'''
        return self.descend(Division, items[1:])

    @matches(t.SecSymbol)
    def handle_secsymbol(self, *items):
        return self.descend(Division, items)

    @matches_subtypes(t.Source)
    def handle_source(self, *items):
        '''Situate the source above the top-level divisions.
        '''
        self.swap(Source, items)
        return self

    @matches(t.Of, t.SessionLaws.Name, t.SessionLaws.Year)
    def handle_session_law(self, *items):
        _, name, year = items
        self.swap(Source, items[1:])
        return self


class Amend(Change):
    'Represents modification of an existing provision.'
    @matches(t.ByAdding)
    def handle_byadding(self, *items):
        return self.replace(Add, *items, transfer=True)


class Add(Change):
    'Represents addition of a new provision.'
    @matches(t.ByAdding)
    def handle_byadding(self, *items):
        'We hit another ByAdding clause in a comma-separated series.'
        return self.parent.descend(Add, *items)

    @matches(t.A, t.Division, t.Numbered)
    def handle_division_numbered(self, *items):
        _, div, _ = items
        return self.descend(Division, div)

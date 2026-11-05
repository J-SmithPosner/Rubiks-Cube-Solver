#Note: U is the color White, 
# R is the color Red, 
# F is the color Green, 
# D is the color Yellow, 
# L is the color Orange, and 
# B is the color Blue
solvedCube = list('UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB')
cubeState = list('UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB')
solution = ''


sides = ['U', 'D', 'R', 'F', 'L', 'B']
edges = [1,3,5,7,10,12,14,16,19,21,23,25,28,30,32,34,37,39,41,43,46,48,50,52]
corners = [0,2,6,8,9,11,15,17,18,20,24,26,27,29,33,35,36,38,42,44,45,47,51,53]
centers = [4,13,22,31,40,49]


faces = {
    'U': [0,1,2,3,4,5,6,7,8],
    'D': [27,28,29,30,31,32,33,34,35],
    'R':[9,10,11,12,13,14,15,16,17],
    'F': [18,19,20,21,22,23,24,25,26],
    'L':[36,37,38,39,40,41,42,43,44],
    'B':[45,46,47,48,49,50,51,52,53]

}

layers = {
    'U': [0,1,2,3,4,5,6,7,8,36,37,38,18,19,20,9,10,11,45,46,47],
    'D': [27,28,29,30,31,32,33,34,35,42,43,44,24,25,26,15,16,17,51,52,53],
    'R':[9,10,11,12,13,14,15,16,17,2,5,8,20,23,26,29,32,35,45,48,51],
    'F': [18,19,20,21,22,23,24,25,26,6,7,8,9,12,15,27,28,29,38,41,44],
    'L':[36,37,38,39,40,41,42,43,44,18,21,24,0,3,6,27,30,33,47,50,53],
    'B':[45,46,47,48,49,50,51,52,53,11,14,17,0,1,2,36,39,42,33,34,35],
    'Middle': [39,40,41,21,22,23,12,13,14,48,49,50]
}


def turn (rot: str, addSol: bool = True) -> None:
    """
Performs a 'turn' on the cube by changing indexes of `cubeState`

Args
------------
rot: `str`
    The type of turn(rotation) that should be performed on the cube \n
    Allowed: U, D, F, B, L, R, M, S, E as well as the suffixes ' and 2 
addSol: `bool`, optional
    Determines whether the turn should be added to the global variable `solution`\n
    Defaults to True 

Outputs
--------
None
    
Side Effects
-----------
The global variable `cubeState` will be updated to reflext `rot`\n
if `addSol` is True, `rot` will be added to the global variable `solution

    """


    
    global cubeState
    global solution

    if addSol:
        solution += rot + ' '
    newCubeState = cubeState.copy()

    #Instead of sepearately coding U, U', and U2, this reruns the code for a single turn 1, 2 or 3 times respectively
    numRots = 0
    if len(rot) == 1:
        numRots = 1
    elif rot[1] == '2':
        numRots = 2
    elif rot[1] == "\'":
        numRots = 3


    for i in range(numRots):

        if rot[0] == 'M':
            newCubeState[19] = cubeState[1]
            newCubeState[22] = cubeState[4]
            newCubeState[25] = cubeState[7]
            newCubeState[28] = cubeState[19]
            newCubeState[31] = cubeState[22]
            newCubeState[34] = cubeState[25]
            newCubeState[52] = cubeState[28]
            newCubeState[49] = cubeState[31]
            newCubeState[46] = cubeState[34]
            newCubeState[1] = cubeState[52]
            newCubeState[4] = cubeState[49]
            newCubeState[7] = cubeState[46]
        elif rot[0] == 'S':
            newCubeState[10] = cubeState[3]
            newCubeState[13] = cubeState[4]
            newCubeState[16] = cubeState[5]
            newCubeState[3] = cubeState[43]
            newCubeState[4] = cubeState[40]
            newCubeState[5] = cubeState[37]
            newCubeState[43] = cubeState[32]
            newCubeState[40] = cubeState[31]
            newCubeState[37] = cubeState[30]
            newCubeState[32] = cubeState[10]
            newCubeState[31] = cubeState[13]
            newCubeState[30] = cubeState[16]
        elif rot[0] == 'E':
            newCubeState[21] = cubeState[39]
            newCubeState[22] = cubeState[40]
            newCubeState[23] = cubeState[41]
            newCubeState[12] = cubeState[21]
            newCubeState[13] = cubeState[22]
            newCubeState[14] = cubeState[23]
            newCubeState[48] = cubeState[12]
            newCubeState[49] = cubeState[13]
            newCubeState[50] = cubeState[14]
            newCubeState[39] = cubeState[48]
            newCubeState[40] = cubeState[49]
            newCubeState[41] = cubeState[50]            

        else:

            #The following statements rotate each piece on the face being turned clockwise
            faceAdder = ['U','R','F','D','L','B'].index(rot[0])*9  
            newCubeState[0+faceAdder] = cubeState[6+faceAdder]    
            newCubeState[1+faceAdder] = cubeState[3+faceAdder]
            newCubeState[2+faceAdder] = cubeState[0+faceAdder]
            newCubeState[3+faceAdder] = cubeState[7+faceAdder]    
            newCubeState[5+faceAdder] = cubeState[1+faceAdder]
            newCubeState[6+faceAdder] = cubeState[8+faceAdder]    
            newCubeState[7+faceAdder] = cubeState[5+faceAdder]
            newCubeState[8+faceAdder] = cubeState[2+faceAdder]

            #The following if Statements turn the pieces on the non-rotated face 90 degrees clockwise around the cube
            if rot[0] == 'U':
                newCubeState[9] = cubeState[45]
                newCubeState[10] = cubeState[46]
                newCubeState[11] = cubeState[47]
                newCubeState[18] = cubeState[9]
                newCubeState[19] = cubeState[10]
                newCubeState[20] = cubeState[11]
                newCubeState[36] = cubeState[18]
                newCubeState[37] = cubeState[19]
                newCubeState[38] = cubeState[20]
                newCubeState[45] = cubeState[36]
                newCubeState[46] = cubeState[37]
                newCubeState[47] = cubeState[38]

            elif rot[0] == 'D':
                newCubeState[15] = cubeState[24]
                newCubeState[16] = cubeState[25]
                newCubeState[17] = cubeState[26]
                newCubeState[24] = cubeState[42]
                newCubeState[25] = cubeState[43]
                newCubeState[26] = cubeState[44]
                newCubeState[42] = cubeState[51]
                newCubeState[43] = cubeState[52]
                newCubeState[44] = cubeState[53]
                newCubeState[51] = cubeState[15]
                newCubeState[52] = cubeState[16]
                newCubeState[53] = cubeState[17]
            elif rot[0] == 'R':
                newCubeState[2] = cubeState[20]
                newCubeState[5] = cubeState[23]
                newCubeState[8] = cubeState[26]
                newCubeState[20] = cubeState[29]
                newCubeState[23] = cubeState[32]
                newCubeState[26] = cubeState[35]
                newCubeState[29] = cubeState[51]
                newCubeState[32] = cubeState[48]
                newCubeState[35] = cubeState[45]
                newCubeState[51] = cubeState[2]
                newCubeState[48] = cubeState[5]
                newCubeState[45] = cubeState[8]
            elif rot[0] == 'L':
                newCubeState[0] = cubeState[53]
                newCubeState[3] = cubeState[50]
                newCubeState[6] = cubeState[47]
                newCubeState[18] = cubeState[0]
                newCubeState[21] = cubeState[3]
                newCubeState[24] = cubeState[6]
                newCubeState[27] = cubeState[18]
                newCubeState[30] = cubeState[21]
                newCubeState[33] = cubeState[24]
                newCubeState[53] = cubeState[27]
                newCubeState[50] = cubeState[30]
                newCubeState[47] = cubeState[33]
            elif rot[0] == 'F':
                newCubeState[6] = cubeState[44]
                newCubeState[7] = cubeState[41]
                newCubeState[8] = cubeState[38]
                newCubeState[44] = cubeState[29]
                newCubeState[41] = cubeState[28]
                newCubeState[38] = cubeState[27]
                newCubeState[29] = cubeState[9]
                newCubeState[28] = cubeState[12]
                newCubeState[27] = cubeState[15]
                newCubeState[9] = cubeState[6]
                newCubeState[12] = cubeState[7]
                newCubeState[15] = cubeState[8]
            elif rot[0] == 'B':
                newCubeState[0] = cubeState[11]
                newCubeState[1] = cubeState[14]
                newCubeState[2] = cubeState[17]
                newCubeState[42] = cubeState[0]
                newCubeState[39] = cubeState[1]
                newCubeState[36] = cubeState[2]
                newCubeState[35] = cubeState[42]
                newCubeState[34] = cubeState[39]
                newCubeState[33] = cubeState[36]
                newCubeState[11] = cubeState[35]
                newCubeState[14] = cubeState[34]
                newCubeState[17] = cubeState[33]

        cubeState = newCubeState.copy()
   
def sexy(m1: str, m2: str, addSol: bool = True) -> None:
    """
Does a sexy algorithm: performs 4 turns on the cube 

(R U R' U') is called a sexy move or sexy algorithm on the rubiks cube
This function performs a general sexy algorithm with ANY first move and ANY second move

Args
---------
m1: `str`
    The first move of the sexy algorithm
m2: `str`
    The second move of the sexy algorithm
addSol: `bool`, optional
    Determines whether the moves should be added to the global variable `solution`\n
    Defaults to `True`


Side Affects
---------
Modifies the `cubeState` by performing the `turn()` function 4 times\n
Adds a special string to solution to denote a sexy move (ex. S(R,U) is the typical sexy move)
    """
    
    global solution
    if addSol:
        solution += 'S(' + m1 + ','+m2+') '

    turn(m1, False)
    turn(m2, False)
    if "'" in m1:
        turn(m1[0], False)
    else:
        turn(m1 + "'", False)

    if "'" in m2:
        turn(m2[0], False)
    else:
        turn(m2 + "'", False)

def algorithm(alg: str, addSol: bool = True) -> None:
    """
Performs an algorithm(set of turns) on the `cubeState`

Args
--------
alg: `str`
    The moves to be performed on the cube (ex. "R U R' U R U2 R' ")
addSol: `bool`, optional
    Determines whether the moves of the algorithm should be added to the global `solution` variable


Side Effect
-----------
`cubeState` is modified by running `turn()` for each turn in `alg` 
    """


    alg = alg.split(' ')
    for letter in alg:
        turn(letter, addSol)

def scramble(moves: str)-> str:
    """
Mixes up a solved cube by performing the `moves` on it

The purpose of this is to function is to pair with the `solve()` function \n
so that `solve()` will solve for a specific `scramble()`\n

Args
---------
moves: `str`
    The set of moves to transform the solved cube into the scrambled cube

Outputs
------------
    A string of the joined entries of the `cubeState`\n
    This matches the necessary input for the `solve()` function


    """

    global cubeState
    cubeState = solvedCube.copy()
    algorithm(moves, False)

    return ''.join(cubeState)




def displayCube() -> None:
    """
    Prints the values of `cubeState` to terminal in a readable format

    Intended for use in debugging
    """

    print(cubeState[0:9])
    print(cubeState[9:18])
    print(cubeState[18:27])
    print(cubeState[27:36])
    print(cubeState[36:45])
    print(cubeState[45:54])

def values(indexes: int | list[int], cube: bool = None) -> str | list[str]:
    """
Returns the values (colors) at the desired indexes of the cube.

Parameters
----------
indexes : int | list[int]
    The indexes to look up.

cube : bool, optional
    Which cube to find values in.
    Default is cubeState.

Returns
-------
str | list[str]
    A single value if indexes is an int,
    otherwise a list of values.
"""
    
    
    
    global cubeState
    newList = []
    if type(indexes) is int:
        if not cube:
            return cubeState[indexes]
        else:
            return cube[indexes]
    else:
        for index in indexes:
            if not cube:
                newList.append(cubeState[index])
            else:
                newList.append(cube[index])

    return newList        

def triangulate(A1: list[int],A2: list[int],A3: list[int] = None) -> list[int]:
    """
Returns the values common to all arrays

Used in conjunction with the arrays/dictionaries `edges`, `corners`, `centers`, `layers`, and `faces` to locate specific pieces

Args
--------
A1, A2, A2: list[int]

`A3` is optional

Uses
---------

Triangulating 3 layers results in the 3 indexes of the corner common to all layers

Triangulating a layer, a layer and edges results in the 2 indexes of the edge common to both layers

Replacing one layer with a face in the above two examples results in a single index of the square on the desired face of the desired piece

Triangulating edges and a face returns indexes of all edges on that face

    """



    if not A3:
        A3 = A1+A2
    return [item for item in set(A1+A2+A3) if (A1+A2+A3).count(item) >= 3]

def pieceIndexes(pieceIndex: int) -> list[int]:
    """
Finds all squares that are part of a specific piece

Args
--------
piece: int
    One index that lies on the desired piece

Outputs
--------
list[int]
    all indexes of squares that lie on the desired piece


    """


    importantSides = []
    for side in sides:
        if pieceIndex in layers[side]:
            importantSides.append(side)

    if len(importantSides) == 1:
        return [pieceIndex]
    elif len(importantSides) == 2:
        return triangulate(edges, layers[importantSides[0]], layers[importantSides[1]])
    else:
        return triangulate(layers[importantSides[0]], layers[importantSides[1]], layers[importantSides[2]])

def pieceSolved(pieceIndex: int) -> bool:
    """
Determines whether a piece is in its final position (solved)
    """

    return all([x in faces[values(x)] for x in pieceIndexes(pieceIndex)]) 

def correctSpot(pieceIndex: int) -> bool:
    """
Determines whether a piece is in the correct spot(not necesarilly solved)

For example, a twisted corner is in the correct spot but not solved
    """

    vals = values(pieceIndexes(pieceIndex))
    return pieceIndex in triangulate(layers[vals[0]], layers[vals[1]], layers[vals[2]])



        
def daisy() -> None: 
    """
Performs the required moves to complete the daisy step

Innitial 
------------------------------------
`cubeState` requirements
    None

Final `cubeState` position:
--------------------------------
`cubeState` requirements
    All edges surrounding the yellow center will be white

    """

    global cubeState
    solved = False

    # while not solved:
    while (len(set(values(triangulate(edges, faces['D'])))) != 1): 
        solved = True
        for i in range(len(cubeState)):
            if i in edges and i not in faces['D'] and cubeState[i] == 'U':
                solved = False
                DaisyPieceSolve(i)
                break

def DaisyPieceSolve(pieceIndex: int) -> None:
    """
Performs the required turns to move a white edge onto the yellow face

Args
--------
pieceIndex: int
    The starting position of the piece that will be moved

Result
----------
    The white piece will be on the yellow face without removing any other white pieces on the yellow face    
    """


    global cubeState
    if pieceIndex in faces['U']: #if the white piece is on the white face, turn the layer that the piece is on twice. No D moves required because this if statement will be the first one to move white pieces to yellow center
        for side in sides:
            if side != 'U' and side != 'D' and pieceIndex in layers[side]:
                while ('U' in values(triangulate(edges, faces['D'],layers[side]))):
                    turn('D')
                turn(side + '2')
                return side + '2'
            
    elif pieceIndex not in faces['D']:
        if pieceIndex not in layers['D'] and pieceIndex not in layers['U']: #If the white piece is in the middle layer
            for side in sides:
                if pieceIndex in layers[side] and pieceIndex not in faces[side]:
                    while ('U' in values(triangulate(edges, faces['D'],layers[side]))):
                        #The while loop checks if the piece above the white edge you're trying to put in is already white
                        #This turns the D layer(yellow) so that you don't mess up any already solved daisy pieces
                        turn('D')
                    while('U' not in values(triangulate(edges, faces['D'],layers[side]))):
                        turn(side)

        else: #If the white piece is on the top or bottop layer bot one of the side faces
            for side in sides:
                if pieceIndex in faces[side]:
                    while ('U' in values(triangulate(edges, faces['D'],layers[side]))):
                        turn('D')
                    turn(side)


            if pieceIndex in layers['U']:#This accounts for how much the piece was moved
                newPieceIndex = pieceIndex+ 4
            else:
                newPieceIndex = pieceIndex - 4
            DaisyPieceSolve(newPieceIndex)
    
def cross() -> None:
    """
Performs the required moves to complete the cross step

Innitial 
------------------------------------
`cubeState` requirements
    All white edges are on the yellow face

Final
--------------------------------
`cubeState` position
    All white edges are solved
    """


    global cubeState
    for side in sides:
        if side != 'D' and side != 'U':
            while not (side in values(triangulate(edges, faces[side], layers['D'])) and 'U' in values(triangulate(edges, faces['D'],layers[side]))):
                turn('D')
            
            turn(side+'2')

def solveRemovef2lCorner(pieceIndex: int) -> None:
    """
Solves a white corner if it didn't start in the white layer

Otherwise, removes that corner from the white layer

Arg:
--------
pieceIndex: int
    The index in `cubeState` of the piece you want to solve/remove

    
    """

    global cubeState
    importantfaces = []
    for val in values(pieceIndexes(pieceIndex)):
        if val != "U":
            importantfaces.append(val)

 
    finalPos = triangulate(faces['U'], layers[importantfaces[0]], layers[importantfaces[1]])
    

    
    if pieceIndex in layers['D']:

        intermediatePos = triangulate(layers[importantfaces[0]], layers[importantfaces[1]], layers['D'])
        while not ('U' in values(intermediatePos) and importantfaces[0] in values(intermediatePos) and importantfaces[1] in values(intermediatePos)):
                turn('D')



        if 'R' in values(intermediatePos):
            sexyStart = 'R'
            if 'F' in values(intermediatePos):
                sexyStart += "'"
        else:
            sexyStart = 'L'
            if 'B' in values(intermediatePos):
                sexyStart += "'"



        while not pieceSolved(finalPos[0]):
            if "'" in sexyStart:
                sexy(sexyStart, "D'")
            else:
                sexy(sexyStart, 'D')


    else:
        if pieceIndex in layers['R']:
            sexyStart = 'R'
            if pieceIndex in layers['F']:
                sexyStart += "'"
        else:
            sexyStart = 'L'
            if pieceIndex in layers['B']:
                sexyStart += "'"

        if "'" in sexyStart:
            sexy(sexyStart, "D'")
        else:
            sexy(sexyStart, 'D')
        
def firstLayer() -> None:
    """
Performs the required moves to solve the first layer

Innitial 
------------------------------------
`cubeState` requirements
    All white edges are solved

Final
--------------------------------
`cubeState` position
    The white layer (`layers['U']`) is solved
        """

    
    while values(layers['U']) != values(layers['U'], solvedCube):
        for i in range(len(cubeState)):
            if i in corners and values(i) =='U' and (not pieceSolved(i)):
                solveRemovef2lCorner(i)

def solveF2LEdge(pieceIndex: int) -> None:
    """
    Solves one non-yellow edge

    Args
    -------
    pieceIndex: int
        The index in `cubeState` of the edge you want to solve
    """



    innitialPieceVals = values(pieceIndexes(pieceIndex))
    if pieceIndexes(pieceIndex)[0] not in faces['D']:
        frontColor = values(pieceIndexes(pieceIndex))[0]
        topColor = values(pieceIndexes(pieceIndex))[1]
    else:
        frontColor = values(pieceIndexes(pieceIndex))[1]
        topColor = values(pieceIndexes(pieceIndex))[0]


    #These next lines determine how many D turns to do so the edge is ready to be put in its slot
    #First Imagine turning the current edge to the Left face(center value = 13) then turn it to its final destination
    centerOrder = [13, 22, 40, 49]
    finalFaceCenter = faces[frontColor][4]
    for i in pieceIndexes(pieceIndex):
        if i not in faces['D']:
            currentFaceCenter = i-3

    numDs = 0
    numDs += centerOrder.index(currentFaceCenter)#Turns current piece to left face
    numDs += (4-centerOrder.index(finalFaceCenter))%4#Turns current piece from left face to final face
    numDs = numDs%4

    for i in range(numDs):
        turn('D')



    #If the slot is on the right start with sexy(topColor), sexy(frontColor') if left, start with sexy(frontColor), sexy(topColor')
    rightPiece = pieceIndexes(triangulate(layers['D'], faces[frontColor], edges)[0]-2) 
    if frontColor in values(rightPiece, solvedCube) and topColor in values(rightPiece, solvedCube):
        turn("D'")
        sexy(topColor + "'", "D'")
        sexy(frontColor, 'D')
    else:
        turn("D")
        sexy(topColor, "D")
        sexy(frontColor + "'", "D'")
               
def secondLayer() -> None:
    """
Performs the required moves to complete the second layer

Innitial 
------------------------------------
`cubeState` requirements
    The white layer (`layers['U']`) is solved

Final
--------------------------------
`cubeState` position
    The white layer (`layers['U']`) and the middle layer (`layers['Middle']`) are solved
        """

    while not values(layers['Middle'])  == values(layers['Middle'], solvedCube): #if an edge on top layer has both non-yellow colors
        if all(['D' in values(pieceIndexes(x)) for x in triangulate(edges, faces['D'])]):
            for square in triangulate(layers['Middle'], edges):
                if not pieceSolved(square):
                    if square in layers['R']:
                        if square in layers['F']:
                            sexy("R'", "D'")
                            sexy("F", "D")
                        else:
                            sexy("R","D")
                            sexy("B'", "D'")
                    else:
                        if square in layers["F"]:
                            sexy("L", "D")
                            sexy("F'", "D'")
                        else:
                            sexy("L'", "D'")
                            sexy("F", "D")
                    break
                   
        else:
            for square in triangulate(layers['D'], edges):
                if 'D' not in values(pieceIndexes(square)):
                    if square in layers['D']:
                        solveF2LEdge(square)

def yellowCross() -> None:
    """
Performs the required moves to complete yellow cros

Innitial 
------------------------------------
`cubeState` requirements
    The first two layers are solved

Final
--------------------------------
`cubeState` position
    All edges on the yellow face are yellow
        """

    while not len(set(values(triangulate(edges, faces['D'])))) == 1: #While the yellow cross is not solved
        if 'D' in values(triangulate(edges, faces['D'])):
            while not (values(32) == 'D' and values(28) != 'D'):
                turn('D')
        turn('F')
        sexy('L','D')
        turn("F'")

def orientEdges() -> None:
    """
Performs the required moves to solve the yellow edges

Innitial 
------------------------------------
`cubeState` requirements
    The first two layers are solved and all edges on the yellow face are yellow

Final
--------------------------------
`cubeState` position
    All yellow edges are solved
        """

    #Checks if the opposite edges are also opposite colors. If they are, do a sune.
    opposites= values([25,52])
    if ('F' in opposites and 'B' in opposites) or('L' in opposites and 'R' in opposites):
        algorithm("L D L' D L D2 L'")

    adjEdges = values([43, 52])
    while not(adjEdges == ['F', 'L'] or adjEdges == ['L', 'B'] or adjEdges == ['B','R'] or adjEdges == ['R','F']):
        turn('D')
        adjEdges = values([43, 52])
        

    algorithm("L D L' D L D2 L'")
    while(not(values(25) == 'F')):
        turn('D')
                
def orientCorners() -> None:
    """
Performs the required moves to orient the Corners

Innitial 
------------------------------------
`cubeState` requirements
    The first two layers and all yellow edges are solved

Final
--------------------------------
`cubeState` position
    All yellow corners are in the correct spot (not necessarilly solved)
        """
    print(format(solution))
    displayCube()
    while not all([correctSpot(piece) for piece in triangulate(corners, faces['D'])]):
        Dturns = 0
        if correctSpot(26):
            Dturns = 3
        elif correctSpot(17):
            Dturns = 2
        elif correctSpot(53):
            Dturns = 1

        for i in range(Dturns):
            turn('D')

        algorithm("D L D' R' D L' D' R")
        
        for i in range(Dturns):
            turn("D'")

def turnCorners() -> None:
    """
Solves the Rubiks Cube

Innitial 
------------------------------------
`cubeState` requirements
    The first two layers and all yellow edges are solved. All yellow corners are oriented.

Final
--------------------------------
`cubeState` position
    Solved
        """



    while not cubeState == solvedCube:
        while not(values(29) == 'D'):
            sexy('R', "U")

        turn('D')

            



def reduceSolution(sol: str) -> str:#Set up this function so that the computer can be given a non-spaced string of moves and turn it into nice looking notation
    """
    Removes any unnecessary moves from solution

    Args
    -------
    sol: str
        The messy solution
    
    Output
    --------
    str
        The clean and concise solution
    """

    #UUU -> U', UU -> U2, U2U -> U', U2L -> U2 L, U'L2 -> U' L2, etc
    sol = sol.split(' ')[0:-1]

    i = 0
    while i< len(sol)-1:#Makes all consecutive moves Us into U, U2, or U'
        if '(' not in sol[i]:
            if ("'" in sol[i+1] or '2' in sol[i+1]) and sol[i] == sol[i+1][0]: #This makes the U' or U2 come before the U so that the following if statements work regardless of which comes first
                temp = sol[i]
                sol[i] = sol[i+1]
                sol[i+1] = temp

            if sol[i] == sol[i+1]: #Turns UU into U2
                sol[i] = sol[i] + '2'
                sol.pop(i+1)
                i-=1

            elif '2' in sol[i] and sol[i][0] == sol[i+1]: #Turns U2U into U'
                sol[i] = sol[i][0] + "'"
                sol.pop(i+1)
                i-=1

            elif "'" in sol[i] and sol[i][0] == sol[i+1]: #Turns U'U into __
                sol[i] = sol[i][0]
                sol.pop(i+1)
                sol.pop(i)
                i-=1
            elif (("'" in sol[i] and '2' in sol[i+1]) or ('2' in sol[i] and "'" in sol[i+1]))and sol[i][0] == sol[i+1][0]:
                sol[i] = sol[i][0]
                sol.pop(i+1)
                i-=1
        else:
            if sol[i+1] == sol[i][0:sol[i].index(')')+1]:
                if 'x' in sol[i]:
                    sol[i] = sol[i][0:-1] + str(int(sol[i][-1])+1)
                else:
                    sol[i] = sol[i] + 'x2'
                sol.pop(i+1)
                i-=1
                                    
                
        i+=1
             
            
    return ' '.join(sol)

def format(sol: str) -> str:
    return reduceSolution(sol)

def solve(facelets: str) -> str:
    """
    Performs the moves to solve a Rubik's Cube

    Generally follows this video explanation: https://www.youtube.com/watch?v=7Ron6MN45LY

    Args
    ---------
    facelets: str
        one long string of characters representing the cube

        This follows the conventions set in the `kociemba` library
    
    Output
    -------------
    str
        A string of Rubik's Cube moves (or shorthands) to solve the Rubik's Cube

        See this sheet for help understanding moves: https://jperm.net/3x3/moves
    
    """


    global cubeState
    global solution
    cubeState = list(facelets)


    daisy()
    solution += '\n'

    cross()
    solution += '\n'

    firstLayer()
    solution += '\n'

    secondLayer()
    solution += '\n'
    

    yellowCross()
    solution += '\n'

    orientEdges()
    solution += '\n'

    orientCorners()
    solution += '\n'

    turnCorners()



    return format(solution)


#OG Test Scramble: F' U2 R B2 L' D F2 R' U B' L2 D2 F' R2 U' L B2 D' R U2

# Solution: L2 F2 D L D L D F'
# D R2 D F2 L2 D B2 
# S(L',D') S(L,D) D' S(R',D')x5 D' S(L',D') D S(L,D) D2 S(L',D')x3 
# D D S(R',D') S(F,D) D'2 S(L',D') S(B,D) D' S(L,D) S(F',D') D S(R,D) S(B',D') 
# F S(L,D) S(L,D) F' 
# L D L' D L D2 L' D' L D L' D L D2 L' D' 

# D S(R,U)x4 D S(R,U)x4 D S(R,U)x4 D


print(solve(scramble("R' B' U' R' B' D2 R D2 F U2 R2 L2 F' D2 B' R2 U2 R2 F' U' R")))

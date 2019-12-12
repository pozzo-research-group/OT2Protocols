#DOE to find  perfect Margarita Recipe assuming addition of: 
#Tequila, Lime Juice, Simple Syrup [3 component DOE]
#Volume constraint, Alcohol Content Constraint

import numpy as np 
import plotly.offline as py
from plotly.offline import download_plotlyjs, init_notebook_mode, plot, iplot
import plotly.graph_objs as go
from sklearn.cluster import KMeans
#initialyze offline plotting
init_notebook_mode(connected=True)

NumIngredients = int(input("How many ingredients in your recipe?"))

#Define sample mass in g
SampleWeight = int(input("How much sample should I prepare? (in grams)"))

#Define min alcohol, min lime juice and min syrup content in vol%
MinConstraints = np.zeros(NumIngredients)
MaxConstraints = np.zeros(NumIngredients)
IngredientDensity = np.zeros(NumIngredients)
for i in range(NumIngredients):
    MinCurrent = float(input("What is the minium constraint on ingredient "+str(i+1)+" in weight fractions?"))
    MinConstraints[i] = MinCurrent
    MaxCurrent = float(input("What is the maximum constraint on ingredient "+str(i+1)+" in weight fractions?"))
    MaxConstraints[i] = MaxCurrent
    DensityCurrent = float(input("What is the density of ingredient "+str(i+1)+" in g/mL?"))
    IngredientDensity[i] = DensityCurrent
print (MinConstraints)
    
#How many samples do you want to test?  Limit to 96 for OT2 loaded with 12 Scintillation Vial Holder
Samples = int(input("How many samples should I prepare? (must be less than 96)"))

#Select a large number of random trials proportional to the number of samples you want to test. 
#Some trials will be discarded because they will violate constraints
RandomTrials = Samples*20

#Generate large number of random composition recipes within the high/low bounds of each component
#These compositions meet constraints but may not meet mixture constraint 1 = x1 + x2 + x3...
RandRecipes = np.random.rand(RandomTrials,NumIngredients)
RandRecipes = RandRecipes*(MaxConstraints-MinConstraints)+MinConstraints

#Add all components for each recipe to see if it is higher or lower than 1
CompSum = np.sum(RandRecipes, axis=1)
#Divide each component by the sum of all components to obtain samples satisfying mixture condition x1+x2+x3+...=1
RandRecipes = RandRecipes/CompSum[:,None]
#Normalization has 'screwed up' some recipes. Some will no longer satisfy constraints. 
#Check high conditions to eliminate from feasible recipe array
UpCheck = RandRecipes>MaxConstraints
#Check low conditions
LowCheck = RandRecipes<MinConstraints
#Combine all checks, any recipe violating any condition must be eliminated
AllCheck = np.append(UpCheck, LowCheck, axis=1)
#Samples that have no violations are added to SafeList 
SafeList = np.any(AllCheck, axis=1)
#Samples violating constraints are added to DeleteList
DeleteList = ~SafeList

#Feasible recipes are a subset of the original recipes
FeasibleRecipes = RandRecipes[DeleteList,:]
print("I have found "+str(len(FeasibleRecipes))+" feasible random recipes out of "+str(RandomTrials)+ " trials, a "+str(100*len(FeasibleRecipes)/RandomTrials)+"% success")

#Apply K-cluster analysis to random recipe distribution to divide feasible space into clusters 
#This ensures recipes sample the feasible space evenly
#Number of Clusters = Final desired sample recipes in feasible space
kmeans = KMeans(n_clusters=Samples, random_state=0).fit(FeasibleRecipes)
#New sample formulations (centroids of the clusters) are evenly distributed in feasible space.
#Note: this does not include samples of the simplex (the edge of the feasible space where one or more components are at low limits)
Centroids = kmeans.cluster_centers_

#Calculate the final formulation by multiplying volume fractions by the total sample volume
FinalFormulations_Weight = np.round(SampleWeight*Centroids,2)

#Convert the weight-basis recipes to volumes needed for OT2 commands
FinalFormulations_Volume = FinalFormulations_Weight/IngredientDensity

Dummy = input("You will need more than these masses (grams) for your stock ingredients: "+str(np.sum(FinalFormulations_Weight, axis=0))+" press enter to continue")

#Plot data in ternary diagram. This is a projection in A,B,C space. Other dimensions are not observable. 
pl_in=dict(type='scatterternary',
                a=FeasibleRecipes[:,0],
                b=FeasibleRecipes[:,1], 
                c=FeasibleRecipes[:,2],
                mode='markers',
                marker=dict(size=5, color='yellow'))

pl_out=dict(type='scatterternary',
                a=RandRecipes[:,0],
                b=RandRecipes[:,1], 
                c=RandRecipes[:,2],
                mode='markers',
                marker=dict(size=5, color='red'))

pl_centroid=dict(type='scatterternary',
                a=Centroids[:,0],
                b=Centroids[:,1], 
                c=Centroids[:,2],
                mode='markers',
                marker=dict(size=5, color='blue'))

data = go.FigureWidget(data=[pl_out, pl_in, pl_centroid])
py.iplot(data, filename='test')
